import { v } from "convex/values";
import { mutation, query } from "./_generated/server";
import { CATEGORY_AMOUNTS } from "./constants";

function normalizeCategory(value: string | undefined) {
  return value ?? "other";
}

export const listTaskCatalog = query({
  args: {},
  handler: async (ctx) => {
    const tasks = await ctx.db.query("taskTypes").collect();
    const sorted = tasks.sort((a, b) => {
      const categoryDiff = normalizeCategory(a.category).localeCompare(normalizeCategory(b.category));
      if (categoryDiff !== 0) return categoryDiff;
      return a.name.localeCompare(b.name);
    });

    const byCategory: Record<string, typeof tasks> = {};
    for (const task of sorted) {
      const category = normalizeCategory(task.category);
      byCategory[category] ??= [];
      byCategory[category].push(task);
    }

    return Object.entries(byCategory).map(([category, items]) => ({
      category,
      target: CATEGORY_AMOUNTS[category] ?? 1,
      tasks: items,
    }));
  },
});

export const getCategoryProgress = query({
  args: { action: v.union(v.literal("complete"), v.literal("amend"), v.literal("ask"), v.literal("optout")) },
  handler: async (ctx, args) => {
    const currentWeek = await ctx.db
      .query("weeks")
      .withIndex("by_closed", (q) => q.eq("closed", false))
      .collect()
      .then((weeks) => weeks.sort((a, b) => b.deadline - a.deadline)[0] ?? null);

    if (!currentWeek) return { currentWeek: null, categories: [] };

    const instances = await ctx.db
      .query("taskInstances")
      .withIndex("by_week_status", (q) => q.eq("weekId", currentWeek._id))
      .collect();

    const categories: Record<string, { category: string; completed: number; total: number }> = {};

    for (const instance of instances) {
      const taskType = await ctx.db.get(instance.taskTypeId);
      if (!taskType) continue;
      const category = normalizeCategory(taskType.category);
      categories[category] ??= { category, completed: 0, total: 0 };

      if (args.action === "complete") {
        if (instance.status === "pending") categories[category].total += 1;
      } else if (args.action === "amend") {
        if (instance.status === "completed") categories[category].total += 1;
      } else {
        categories[category].total += 1;
      }

      if (instance.status === "completed") categories[category].completed += 1;
    }

    return { currentWeek, categories: Object.values(categories) };
  },
});

export const getTasksByCategory = query({
  args: {
    category: v.string(),
    action: v.union(v.literal("complete"), v.literal("amend"), v.literal("ask")),
  },
  handler: async (ctx, args) => {
    const currentWeek = await ctx.db
      .query("weeks")
      .withIndex("by_closed", (q) => q.eq("closed", false))
      .collect()
      .then((weeks) => weeks.sort((a, b) => b.deadline - a.deadline)[0] ?? null);

    if (!currentWeek) return { currentWeek: null, tasks: [] };

    const instances = await ctx.db
      .query("taskInstances")
      .withIndex("by_week_status", (q) => q.eq("weekId", currentWeek._id))
      .collect();

    const tasks: Array<{ instanceId: string; name: string; estimatedDurationMinutes?: number; status: string }> = [];

    for (const instance of instances) {
      const taskType = await ctx.db.get(instance.taskTypeId);
      if (!taskType) continue;
      if (normalizeCategory(taskType.category) !== args.category) continue;

      if (args.action === "complete" && instance.status !== "pending") continue;
      if (args.action === "amend" && instance.status !== "completed") continue;

      tasks.push({
        instanceId: instance._id,
        name: taskType.name,
        estimatedDurationMinutes: taskType.estimatedDurationMinutes,
        status: instance.status,
      });
    }

    tasks.sort((a, b) => a.name.localeCompare(b.name));
    return { currentWeek, tasks };
  },
});

export const getTaskInstructions = query({
  args: { taskInstanceId: v.id("taskInstances") },
  handler: async (ctx, args) => {
    const instance = await ctx.db.get(args.taskInstanceId);
    if (!instance) return null;
    const taskType = await ctx.db.get(instance.taskTypeId);
    if (!taskType) return null;
    return { instance, taskType };
  },
});

export const completeTask = mutation({
  args: {
    taskInstanceId: v.id("taskInstances"),
    telegramId: v.int64(),
    messageId: v.optional(v.int64()),
  },
  handler: async (ctx, args) => {
    const person = await ctx.db
      .query("people")
      .withIndex("by_telegramId", (q) => q.eq("telegramId", args.telegramId))
      .unique();

    if (!person) return { ok: false as const, error: "not_registered" };

    const taskInstance = await ctx.db.get(args.taskInstanceId);
    if (!taskInstance || taskInstance.status !== "pending") {
      return { ok: false as const, error: "invalid_task" };
    }

    const optOut = await ctx.db
      .query("taskOptOuts")
      .withIndex("by_person_task", (q) => q.eq("personId", person._id).eq("taskTypeId", taskInstance.taskTypeId))
      .unique();

    if (optOut) {
      const taskType = await ctx.db.get(taskInstance.taskTypeId);
      return {
        ok: false as const,
        error: "opted_out",
        taskName: taskType?.name ?? "Unknown task",
        reason: optOut.reason,
      };
    }

    await ctx.db.patch(taskInstance._id, {
      status: "completed",
      completedBy: person._id,
      completedAt: Date.now(),
    });

    await ctx.db.insert("completionLog", {
      taskInstanceId: taskInstance._id,
      personId: person._id,
      action: "completed",
      timestamp: Date.now(),
      messageId: args.messageId,
    });

    const currentWeek = await ctx.db.get(taskInstance.weekId);
    if (!currentWeek) return { ok: false as const, error: "missing_week" };

    const allInstances = await ctx.db
      .query("taskInstances")
      .withIndex("by_week_status", (q) => q.eq("weekId", currentWeek._id))
      .collect();

    const completedCount = allInstances.filter((t) => t.status === "completed").length;
    const total = Object.values(CATEGORY_AMOUNTS).reduce((acc, value) => acc + value, 0);
    const remaining = total - completedCount;

    const personalCount = allInstances.filter((t) => t.completedBy === person._id).length;

    const taskType = await ctx.db.get(taskInstance.taskTypeId);

    return {
      ok: true as const,
      personName: person.name,
      taskName: taskType?.name ?? "Unknown task",
      personalCount,
      remaining,
      weekId: currentWeek._id,
    };
  },
});

export const amendTask = mutation({
  args: {
    taskInstanceId: v.id("taskInstances"),
    telegramId: v.int64(),
    messageId: v.optional(v.int64()),
  },
  handler: async (ctx, args) => {
    const person = await ctx.db
      .query("people")
      .withIndex("by_telegramId", (q) => q.eq("telegramId", args.telegramId))
      .unique();

    if (!person) return { ok: false as const, error: "not_registered" };

    const taskInstance = await ctx.db.get(args.taskInstanceId);
    if (!taskInstance || taskInstance.status !== "completed") {
      return { ok: false as const, error: "invalid_task" };
    }

    const taskType = await ctx.db.get(taskInstance.taskTypeId);
    const originalCompleter = taskInstance.completedBy ? await ctx.db.get(taskInstance.completedBy) : null;

    await ctx.db.patch(taskInstance._id, {
      status: "pending",
      completedBy: undefined,
      completedAt: undefined,
    });

    await ctx.db.insert("completionLog", {
      taskInstanceId: taskInstance._id,
      personId: person._id,
      action: "amended",
      timestamp: Date.now(),
      messageId: args.messageId,
    });

    return {
      ok: true as const,
      taskName: taskType?.name ?? "Unknown task",
      amendedBy: person.name,
      originalCompleter: originalCompleter?.name ?? "Unknown",
    };
  },
});

export const getMyStats = query({
  args: { telegramId: v.int64() },
  handler: async (ctx, args) => {
    const person = await ctx.db
      .query("people")
      .withIndex("by_telegramId", (q) => q.eq("telegramId", args.telegramId))
      .unique();

    if (!person) return { ok: false as const, error: "not_registered" };

    const currentWeek = await ctx.db
      .query("weeks")
      .withIndex("by_closed", (q) => q.eq("closed", false))
      .collect()
      .then((weeks) => weeks.sort((a, b) => b.deadline - a.deadline)[0] ?? null);

    let weekTasks: Array<{ name: string }> = [];
    if (currentWeek) {
      const instances = await ctx.db
        .query("taskInstances")
        .withIndex("by_completedBy_week", (q) => q.eq("completedBy", person._id).eq("weekId", currentWeek._id))
        .collect();

      weekTasks = [];
      for (const instance of instances) {
        const taskType = await ctx.db.get(instance.taskTypeId);
        if (taskType) weekTasks.push({ name: taskType.name });
      }
      weekTasks.sort((a, b) => a.name.localeCompare(b.name));
    }

    const allTime = await ctx.db
      .query("taskInstances")
      .collect()
      .then((items) => items.filter((i) => i.completedBy === person._id).length);

    const optOuts = await ctx.db
      .query("taskOptOuts")
      .collect()
      .then((items) => items.filter((item) => item.personId === person._id));

    const optOutNames: string[] = [];
    for (const optOut of optOuts) {
      const taskType = await ctx.db.get(optOut.taskTypeId);
      if (taskType) optOutNames.push(taskType.name);
    }
    optOutNames.sort();

    return {
      ok: true as const,
      person,
      currentWeek,
      weekTasks,
      allTime,
      optOutNames,
    };
  },
});
