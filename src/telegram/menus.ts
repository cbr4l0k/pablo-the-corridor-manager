import { CATEGORY_AMOUNTS, CATEGORY_EMOJIS } from "../domain/constants";
import type { InlineKeyboardMarkup } from "../types/telegram";

export function createMainMenu(isPrivate: boolean): InlineKeyboardMarkup {
  if (isPrivate) {
    return {
      inline_keyboard: [
        [
          { text: "📋 View Status", callback_data: "status" },
          { text: "✅ Complete Task", callback_data: "complete:categories" },
        ],
        [
          { text: "❌ Amend Task", callback_data: "amend:categories" },
          { text: "❓ Ask Instructions", callback_data: "ask:categories" },
        ],
        [
          { text: "🚫 Opt Out", callback_data: "optout:categories" },
          { text: "📊 My Stats", callback_data: "mystats" },
        ],
        [
          { text: "🗺️ Show Map", callback_data: "map" },
          { text: "💡 Help", callback_data: "help" },
        ],
      ],
    };
  }

  return {
    inline_keyboard: [
      [
        { text: "📋 View Status", callback_data: "status" },
        { text: "📝 List Tasks", callback_data: "tasks" },
      ],
      [
        { text: "👥 Who Opted Out", callback_data: "whooptedout" },
        { text: "💡 Help", callback_data: "help" },
      ],
    ],
  };
}

export function createCategoryMenu(
  action: "complete" | "amend" | "ask" | "optout",
  categories: Array<{ category: string; completed: number; total: number }>,
): InlineKeyboardMarkup {
  const sorted = [...categories].sort((a, b) => a.category.localeCompare(b.category));
  const rows: InlineKeyboardMarkup["inline_keyboard"] = [];
  let row: NonNullable<InlineKeyboardMarkup["inline_keyboard"]>[number] = [];

  for (const item of sorted) {
    if (item.total === 0) continue;
    const emoji = CATEGORY_EMOJIS[item.category] ?? "📦";
    const target = CATEGORY_AMOUNTS[item.category] ?? 1;
    row.push({
      text: `${emoji} ${capitalize(item.category)} (${item.completed}/${target})`,
      callback_data: `${action}:category:${item.category}`,
    });
    if (row.length === 2) {
      rows.push(row);
      row = [];
    }
  }

  if (row.length > 0) rows.push(row);
  rows.push([{ text: "« Back to Menu", callback_data: "menu" }]);

  return { inline_keyboard: rows };
}

export function createTaskMenu(
  action: "complete" | "amend" | "ask",
  fallbackBack: string,
  tasks: Array<{ instanceId: string; name: string; estimatedDurationMinutes?: number; status: string }>,
): InlineKeyboardMarkup {
  const rows: InlineKeyboardMarkup["inline_keyboard"] = tasks.map((task) => {
    const statusEmoji = task.status === "completed" ? "✅" : "⏳";
    const duration = task.estimatedDurationMinutes ? ` - ${task.estimatedDurationMinutes}min` : "";
    return [{ text: `${statusEmoji} ${task.name}${duration}`, callback_data: `${action}:task:${task.instanceId}` }];
  });
  rows.push([{ text: "« Back to Categories", callback_data: fallbackBack }]);
  return { inline_keyboard: rows };
}

function capitalize(value: string): string {
  if (!value) return value;
  return value[0].toUpperCase() + value.slice(1);
}
