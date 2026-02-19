import type { MutationCtx } from "../_generated/server";

export async function findByName(
  ctx: MutationCtx,
  table: "taskTypes",
  name: string,
) {
  return ctx.db
    .query(table)
    .withIndex("by_name", (q) => q.eq("name", name))
    .unique();
}
