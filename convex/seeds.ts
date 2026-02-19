import type { MutationCtx } from "./_generated/server";
import { internalMutation, mutation } from "./_generated/server";
import { TASK_TYPE_DEFINITIONS } from "./seedData";

function getIsoWeekYearWeek(date: Date) {
  const utcDate = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  const dayNum = utcDate.getUTCDay() || 7;
  utcDate.setUTCDate(utcDate.getUTCDate() + 4 - dayNum);
  const isoYear = utcDate.getUTCFullYear();
  const yearStart = new Date(Date.UTC(isoYear, 0, 1));
  const weekNo = Math.ceil((((utcDate.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
  return { year: isoYear, weekNumber: weekNo };
}

function getWeekStartAndDeadline(now: Date) {
  const day = now.getUTCDay() || 7;
  const monday = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
  monday.setUTCDate(monday.getUTCDate() - (day - 1));
  monday.setUTCHours(0, 0, 0, 0);

  const deadline = new Date(monday.getTime());
  deadline.setUTCDate(deadline.getUTCDate() + 4);
  deadline.setUTCHours(12, 0, 0, 0);

  return { startDateMs: monday.getTime(), deadlineMs: deadline.getTime() };
}

type DbCtx = Pick<MutationCtx, "db">;

async function seedTaskTypes(ctx: DbCtx) {
  const maybeOne = await ctx.db.query("taskTypes").take(1);
  if (maybeOne.length > 0) {
    return { inserted: 0, skipped: TASK_TYPE_DEFINITIONS.length, alreadySeeded: true };
  }

  let inserted = 0;
  for (const task of TASK_TYPE_DEFINITIONS) {
    const existing = await ctx.db
      .query("taskTypes")
      .withIndex("by_name", (q) => q.eq("name", task.name))
      .unique();

    if (existing) {
      continue;
    }

    await ctx.db.insert("taskTypes", {
      name: task.name,
      category: task.category,
      description: task.description,
      instructions: task.instructions,
      frequency: "weekly",
      estimatedDurationMinutes: task.estimatedDurationMinutes,
      location: task.location,
    });
    inserted += 1;
  }

  return { inserted, skipped: TASK_TYPE_DEFINITIONS.length - inserted, alreadySeeded: false };
}

async function createCurrentWeekWithTasks(ctx: DbCtx) {
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

  if (!week) {
    throw new Error("Failed to create or load current week");
  }

  const taskTypes = await ctx.db.query("taskTypes").collect();
  let createdTaskInstances = 0;

  for (const taskType of taskTypes) {
    const existingInstance = await ctx.db
      .query("taskInstances")
      .withIndex("by_week_task", (q) => q.eq("weekId", week._id).eq("taskTypeId", taskType._id))
      .unique();

    if (existingInstance) {
      continue;
    }

    await ctx.db.insert("taskInstances", {
      weekId: week._id,
      taskTypeId: taskType._id,
      status: "pending",
    });
    createdTaskInstances += 1;
  }

  return {
    year,
    weekNumber,
    weekId: week._id,
    weekCreated,
    createdTaskInstances,
    totalTaskTypes: taskTypes.length,
  };
}

export const seedTaskTypesIfEmpty = internalMutation({
  args: {},
  handler: async (ctx) => seedTaskTypes(ctx),
});

export const createCurrentWeekWithTasksIfMissing = internalMutation({
  args: {},
  handler: async (ctx) => createCurrentWeekWithTasks(ctx),
});

export const bootstrapSeed = mutation({
  args: {},
  handler: async (ctx) => {
    const taskTypeResult = await seedTaskTypes(ctx);
    const weekResult = await createCurrentWeekWithTasks(ctx);

    return {
      taskTypes: taskTypeResult,
      week: weekResult,
    };
  },
});
