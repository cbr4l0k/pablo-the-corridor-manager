import { v } from "convex/values";
import type { MutationCtx } from "./_generated/server";
import { mutation, query } from "./_generated/server";
import { getIsoWeekYearWeek, getWeekStartAndDeadline } from "./lib/time";

async function ensureCurrentWeek(ctx: MutationCtx) {
  const now = new Date();
  const { year, weekNumber } = getIsoWeekYearWeek(now);
  const { startDateMs, deadlineMs } = getWeekStartAndDeadline(now);

  let week = await ctx.db
    .query("weeks")
    .withIndex("by_year_week", (q) => q.eq("year", year).eq("weekNumber", weekNumber))
    .unique();

  let weekCreated = false;
  if (!week) {
    const weekId = await ctx.db.insert("weeks", {
      year,
      weekNumber,
      startDate: startDateMs,
      deadline: deadlineMs,
      closed: false,
    });
    week = await ctx.db.get(weekId);
    weekCreated = true;
  }

  if (!week) throw new Error("Unable to resolve current week");

  return { week, weekCreated };
}

export const getActiveWeek = query({
  args: {},
  handler: async (ctx) => {
    const weeks = await ctx.db.query("weeks").withIndex("by_closed", (q) => q.eq("closed", false)).collect();
    return weeks.sort((a, b) => b.deadline - a.deadline)[0] ?? null;
  },
});

export const ensureActiveWeek = mutation({
  args: {},
  handler: async (ctx) => {
    const { week, weekCreated } = await ensureCurrentWeek(ctx);

    const taskTypes = await ctx.db.query("taskTypes").collect();
    let createdTaskInstances = 0;

    for (const taskType of taskTypes) {
      const existing = await ctx.db
        .query("taskInstances")
        .withIndex("by_week_task", (q) => q.eq("weekId", week._id).eq("taskTypeId", taskType._id))
        .unique();
      if (existing) continue;

      await ctx.db.insert("taskInstances", {
        weekId: week._id,
        taskTypeId: taskType._id,
        status: "pending",
      });
      createdTaskInstances += 1;
    }

    return {
      week,
      weekCreated,
      createdTaskInstances,
      totalTaskTypes: taskTypes.length,
    };
  },
});

export const closeWeek = mutation({
  args: { weekId: v.id("weeks") },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.weekId, { closed: true });
    return { ok: true };
  },
});
