import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

export const getByTelegramId = query({
  args: { telegramId: v.int64() },
  handler: async (ctx, args) => {
    return ctx.db
      .query("people")
      .withIndex("by_telegramId", (q) => q.eq("telegramId", args.telegramId))
      .unique();
  },
});

export const registerIfMissing = mutation({
  args: {
    telegramId: v.int64(),
    name: v.string(),
    username: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("people")
      .withIndex("by_telegramId", (q) => q.eq("telegramId", args.telegramId))
      .unique();

    if (existing) {
      return { person: existing, created: false };
    }

    const personId = await ctx.db.insert("people", {
      telegramId: args.telegramId,
      name: args.name,
      username: args.username,
      joinedDate: Date.now(),
      active: true,
    });

    const person = await ctx.db.get(personId);
    return { person, created: true };
  },
});

export const listActive = query({
  args: {},
  handler: async (ctx) => {
    return ctx.db
      .query("people")
      .collect()
      .then((people) => people.filter((p) => p.active));
  },
});
