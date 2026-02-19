export const CATEGORY_AMOUNTS: Record<string, number> = {
  toilet: 2,
  shower: 2,
  kitchen: 3,
  fridge: 2,
  hallway: 1,
  laundry: 1,
  trash: 2,
  other: 1,
};

export const CATEGORY_EMOJIS: Record<string, string> = {
  toilet: "🚽",
  shower: "🚿",
  kitchen: "🍳",
  fridge: "❄️",
  hallway: "🚪",
  laundry: "🧺",
  trash: "🗑️",
  other: "📦",
};

export const PRIVATE_ONLY_ACTIONS = new Set([
  "complete",
  "amend",
  "ask",
  "optout",
  "mystats",
  "map",
]);

export const WEEKLY_REMINDER_DAYS = [2, 5] as const;
export const WEEKLY_REMINDER_HOURS = [10, 18] as const;

export const WEEK_ROLLOVER_HOUR = 23;
export const WEEK_ROLLOVER_MINUTE = 59;
