import { v } from "convex/values";
import { query } from "./_generated/server";
import { CATEGORY_AMOUNTS } from "./constants";

function getProgressBar(completed: number, total: number) {
  const progress = total > 0 ? Math.floor((completed / total) * 10) : 0;
  return "█".repeat(progress) + "░".repeat(10 - progress);
}

export const getStatusDetailed = query({
  args: {},
  handler: async (ctx) => {
    const currentWeek = await ctx.db
      .query("weeks")
      .withIndex("by_closed", (q) => q.eq("closed", false))
      .collect()
      .then((weeks) => weeks.sort((a, b) => b.deadline - a.deadline)[0] ?? null);

    if (!currentWeek) return { ok: false as const, error: "no_active_week" };

    const instances = await ctx.db
      .query("taskInstances")
      .withIndex("by_week_status", (q) => q.eq("weekId", currentWeek._id))
      .collect();

    const byCategory: Record<string, { completed: number; total: number }> = {};
    const completedTasks: Array<{ taskName: string; personName: string | null }> = [];

    for (const instance of instances) {
      const taskType = await ctx.db.get(instance.taskTypeId);
      if (!taskType) continue;
      const category = taskType.category ?? "other";

      byCategory[category] ??= { completed: 0, total: CATEGORY_AMOUNTS[category] ?? 1 };
      if (instance.status === "completed") {
        byCategory[category].completed += 1;
        const person = instance.completedBy ? await ctx.db.get(instance.completedBy) : null;
        completedTasks.push({
          taskName: taskType.name,
          personName: person?.name ?? null,
        });
      }
    }

    const completedCount = completedTasks.length;
    const overallTotal = Object.keys(byCategory).reduce((acc, cat) => acc + (CATEGORY_AMOUNTS[cat] ?? 1), 0);
    const done = Object.entries(byCategory).every(([cat, stats]) => stats.completed >= (CATEGORY_AMOUNTS[cat] ?? 1));

    const activePeople = await ctx.db
      .query("people")
      .collect()
      .then((items) => items.filter((p) => p.active));
    const completedBy = new Set(
      instances
        .filter((item) => item.status === "completed" && item.completedBy)
        .map((item) => item.completedBy!),
    );
    const notContributed = activePeople.filter((person) => !completedBy.has(person._id)).map((p) => p.name);

    return {
      ok: true as const,
      currentWeek,
      byCategory,
      completedTasks,
      completedCount,
      overallTotal,
      overallBar: getProgressBar(completedCount, overallTotal),
      done,
      notContributed,
    };
  },
});

export const getStatusSummary = query({
  args: {},
  handler: async (ctx) => {
    const currentWeek = await ctx.db
      .query("weeks")
      .withIndex("by_closed", (q) => q.eq("closed", false))
      .collect()
      .then((weeks) => weeks.sort((a, b) => b.deadline - a.deadline)[0] ?? null);

    if (!currentWeek) return { ok: false as const, error: "no_active_week" };

    const instances = await ctx.db
      .query("taskInstances")
      .withIndex("by_week_status", (q) => q.eq("weekId", currentWeek._id))
      .collect();
    const completedCount = instances.filter((task) => task.status === "completed").length;
    const total = Object.values(CATEGORY_AMOUNTS).reduce((acc, value) => acc + value, 0);

    return {
      ok: true as const,
      currentWeek,
      completedCount,
      total,
      overallBar: getProgressBar(completedCount, total),
    };
  },
});

export const getWeekSnapshot = query({
  args: { weekId: v.id("weeks") },
  handler: async (ctx, args) => {
    const week = await ctx.db.get(args.weekId);
    if (!week) return null;

    const instances = await ctx.db
      .query("taskInstances")
      .withIndex("by_week_status", (q) => q.eq("weekId", args.weekId))
      .collect();

    const completed = instances.filter((t) => t.status === "completed");
    const total = Object.values(CATEGORY_AMOUNTS).reduce((acc, value) => acc + value, 0);

    const contributions: Record<string, number> = {};
    for (const task of completed) {
      if (!task.completedBy) continue;
      const person = await ctx.db.get(task.completedBy);
      if (!person) continue;
      contributions[person.name] = (contributions[person.name] ?? 0) + 1;
    }

    const activePeople = await ctx.db
      .query("people")
      .collect()
      .then((items) => items.filter((p) => p.active));

    const nonContributors = activePeople
      .map((p) => p.name)
      .filter((name) => !(name in contributions))
      .sort((a, b) => a.localeCompare(b));

    return {
      week,
      total,
      completedCount: completed.length,
      remaining: total - completed.length,
      contributions,
      nonContributors,
    };
  },
});
