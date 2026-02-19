import { makeFunctionReference } from "convex/server";

export const refs = {
  people: {
    registerIfMissing: makeFunctionReference<"mutation">("people:registerIfMissing"),
  },
  tasks: {
    listTaskCatalog: makeFunctionReference<"query">("tasks:listTaskCatalog"),
    getCategoryProgress: makeFunctionReference<"query">("tasks:getCategoryProgress"),
    getTasksByCategory: makeFunctionReference<"query">("tasks:getTasksByCategory"),
    getTaskInstructions: makeFunctionReference<"query">("tasks:getTaskInstructions"),
    completeTask: makeFunctionReference<"mutation">("tasks:completeTask"),
    amendTask: makeFunctionReference<"mutation">("tasks:amendTask"),
    getMyStats: makeFunctionReference<"query">("tasks:getMyStats"),
  },
  status: {
    getStatusDetailed: makeFunctionReference<"query">("status:getStatusDetailed"),
    getStatusSummary: makeFunctionReference<"query">("status:getStatusSummary"),
  },
  optouts: {
    createOptOut: makeFunctionReference<"mutation">("optouts:createOptOut"),
    listWhoOptedOut: makeFunctionReference<"query">("optouts:listWhoOptedOut"),
  },
  weeks: {
    ensureActiveWeek: makeFunctionReference<"mutation">("weeks:ensureActiveWeek"),
  },
  jobs: {
    buildReminderPayload: makeFunctionReference<"action">("jobs:buildReminderPayload"),
    checkAndRollover: makeFunctionReference<"action">("jobs:checkAndRollover"),
  },
};
