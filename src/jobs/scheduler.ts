import { WEEKLY_REMINDER_DAYS, WEEKLY_REMINDER_HOURS, WEEK_ROLLOVER_HOUR, WEEK_ROLLOVER_MINUTE } from "../domain/constants";
import { refs } from "../convex/refs";
import type { TelegramClient } from "../telegram/client";
import type { ConvexHttpClient } from "convex/browser";

function key(date: Date) {
  return `${date.getUTCFullYear()}-${date.getUTCMonth()}-${date.getUTCDate()}-${date.getUTCHours()}-${date.getUTCMinutes()}`;
}

export function startSchedulers(params: {
  convex: ConvexHttpClient;
  telegram: TelegramClient;
  groupChatId: number;
  tickMs: number;
}) {
  const { convex, telegram, groupChatId, tickMs } = params;
  const fired = new Set<string>();

  setInterval(async () => {
    const now = new Date();
    const day = now.getUTCDay();
    const hour = now.getUTCHours();
    const minute = now.getUTCMinutes();

    const minuteKey = key(now);
    if (fired.has(minuteKey)) return;

    if (WEEKLY_REMINDER_DAYS.includes(day as any) && WEEKLY_REMINDER_HOURS.includes(hour as any) && minute === 0) {
      const payload = await convex.action(refs.jobs.buildReminderPayload, {});
      if (payload.ok) {
        await telegram.sendMessage({
          chatId: groupChatId,
          text: payload.message,
          parseMode: "Markdown",
        });
      }
      fired.add(minuteKey);
      return;
    }

    if (hour === WEEK_ROLLOVER_HOUR && minute === WEEK_ROLLOVER_MINUTE) {
      const rollover = await convex.action(refs.jobs.checkAndRollover, {});
      if (rollover.ok) {
        if (rollover.summaryMessage) {
          await telegram.sendMessage({ chatId: groupChatId, text: rollover.summaryMessage, parseMode: "Markdown" });
        }
        if (rollover.newWeekAnnouncement) {
          await telegram.sendMessage({
            chatId: groupChatId,
            text: rollover.newWeekAnnouncement,
            parseMode: "Markdown",
          });
        }
      }
      fired.add(minuteKey);
      return;
    }
  }, tickMs);
}
