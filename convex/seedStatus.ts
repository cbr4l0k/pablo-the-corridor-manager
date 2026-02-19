import { query } from "./_generated/server";

export const getSeedStatus = query({
  args: {},
  handler: async (ctx) => {
    const [taskTypes, weeks, taskInstances] = await Promise.all([
      ctx.db.query("taskTypes").collect(),
      ctx.db.query("weeks").collect(),
      ctx.db.query("taskInstances").collect(),
    ]);

    return {
      taskTypeCount: taskTypes.length,
      weekCount: weeks.length,
      taskInstanceCount: taskInstances.length,
    };
  },
});
