import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

export const createOptOut = mutation({
  args: {
    telegramId: v.int64(),
    taskQuery: v.string(),
    reason: v.string(),
  },
  handler: async (ctx, args) => {
    const person = await ctx.db
      .query("people")
      .withIndex("by_telegramId", (q) => q.eq("telegramId", args.telegramId))
      .unique();
    if (!person) return { ok: false as const, error: "not_registered" };

    const allTaskTypes = await ctx.db.query("taskTypes").collect();
    const taskType = allTaskTypes.find((task) =>
      task.name.toLowerCase().includes(args.taskQuery.toLowerCase()),
    );

    if (!taskType) {
      return { ok: false as const, error: "task_not_found", taskQuery: args.taskQuery };
    }

    const existing = await ctx.db
      .query("taskOptOuts")
      .withIndex("by_person_task", (q) => q.eq("personId", person._id).eq("taskTypeId", taskType._id))
      .unique();

    if (existing) {
      return {
        ok: false as const,
        error: "already_opted_out",
        taskName: taskType.name,
        reason: existing.reason,
      };
    }

    await ctx.db.insert("taskOptOuts", {
      personId: person._id,
      taskTypeId: taskType._id,
      reason: args.reason,
      createdAt: Date.now(),
    });

    return {
      ok: true as const,
      personName: person.name,
      taskName: taskType.name,
      reason: args.reason,
    };
  },
});

export const listWhoOptedOut = query({
  args: { taskQuery: v.optional(v.string()) },
  handler: async (ctx, args) => {
    const optOuts = await ctx.db.query("taskOptOuts").collect();

    const rows: Array<{ taskName: string; personName: string; reason: string }> = [];
    for (const optOut of optOuts) {
      const person = await ctx.db.get(optOut.personId);
      const taskType = await ctx.db.get(optOut.taskTypeId);
      if (!person || !taskType) continue;
      rows.push({ taskName: taskType.name, personName: person.name, reason: optOut.reason });
    }

    rows.sort((a, b) => a.taskName.localeCompare(b.taskName) || a.personName.localeCompare(b.personName));

    if (!args.taskQuery) {
      return { ok: true as const, rows };
    }

    const filtered = rows.filter((row) => row.taskName.toLowerCase().includes(args.taskQuery!.toLowerCase()));
    return {
      ok: true as const,
      taskQuery: args.taskQuery,
      rows: filtered,
    };
  },
});
