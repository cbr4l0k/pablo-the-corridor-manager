import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  people: defineTable({
    telegramId: v.int64(),
    name: v.string(),
    username: v.optional(v.string()),
    joinedDate: v.number(),
    active: v.boolean(),
  }).index("by_telegramId", ["telegramId"]),

  taskTypes: defineTable({
    name: v.string(),
    category: v.string(),
    description: v.string(),
    instructions: v.string(),
    mediaFileId: v.optional(v.string()),
    frequency: v.string(),
    estimatedDurationMinutes: v.optional(v.number()),
    location: v.optional(v.string()),
  }).index("by_name", ["name"]),

  taskOptOuts: defineTable({
    personId: v.id("people"),
    taskTypeId: v.id("taskTypes"),
    reason: v.string(),
    createdAt: v.number(),
  })
    .index("by_person_task", ["personId", "taskTypeId"])
    .index("by_taskTypeId", ["taskTypeId"]),

  weeks: defineTable({
    year: v.number(),
    weekNumber: v.number(),
    startDate: v.number(),
    deadline: v.number(),
    closed: v.boolean(),
  })
    .index("by_year_week", ["year", "weekNumber"])
    .index("by_closed", ["closed"]),

  taskInstances: defineTable({
    weekId: v.id("weeks"),
    taskTypeId: v.id("taskTypes"),
    status: v.union(v.literal("pending"), v.literal("completed"), v.literal("skipped")),
    completedBy: v.optional(v.id("people")),
    completedAt: v.optional(v.number()),
    notes: v.optional(v.string()),
  })
    .index("by_week_task", ["weekId", "taskTypeId"])
    .index("by_week_status", ["weekId", "status"])
    .index("by_completedBy_week", ["completedBy", "weekId"]),

  completionLog: defineTable({
    taskInstanceId: v.id("taskInstances"),
    personId: v.optional(v.id("people")),
    action: v.string(),
    timestamp: v.number(),
    messageId: v.optional(v.int64()),
  })
    .index("by_taskInstanceId", ["taskInstanceId"])
    .index("by_personId", ["personId"]),

  penalties: defineTable({
    personId: v.id("people"),
    weekId: v.id("weeks"),
    amountEur: v.number(),
    penaltyType: v.string(),
    paid: v.boolean(),
    paidAt: v.optional(v.number()),
    paidVia: v.optional(v.string()),
  })
    .index("by_person_week", ["personId", "weekId"])
    .index("by_weekId", ["weekId"]),
});
