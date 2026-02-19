import { action } from "./_generated/server";
import { makeFunctionReference } from "convex/server";
import { CATEGORY_AMOUNTS } from "./constants";

const statusGetDetailed = makeFunctionReference<"query">("status:getStatusDetailed");
const weeksGetActive = makeFunctionReference<"query">("weeks:getActiveWeek");
const weeksEnsureActive = makeFunctionReference<"mutation">("weeks:ensureActiveWeek");
const statusGetWeekSnapshot = makeFunctionReference<"query">("status:getWeekSnapshot");
const weeksClose = makeFunctionReference<"mutation">("weeks:closeWeek");

function progressBar(completed: number, total: number) {
  const progress = total > 0 ? Math.floor((completed / total) * 10) : 0;
  return "█".repeat(progress) + "░".repeat(10 - progress);
}

export const buildReminderPayload = action({
  args: {},
  handler: async (ctx) => {
    const status = await ctx.runQuery(statusGetDetailed, {});
    if (!status.ok) return { ok: false as const, error: "no_active_week" };

    const total = Object.values(CATEGORY_AMOUNTS).reduce((acc, value) => acc + value, 0);
    const remaining = total - status.completedCount;

    const now = Date.now();
    const daysUntilDeadline = Math.floor((status.currentWeek.deadline - now) / (24 * 60 * 60 * 1000));

    const deadlineLabel =
      daysUntilDeadline < 0
        ? "⚠️ *OVERDUE!*"
        : daysUntilDeadline === 0
          ? "⏰ *Due TODAY!*"
          : daysUntilDeadline === 1
            ? "⏰ *Due TOMORROW!*"
            : `⏰ Due in *${daysUntilDeadline} days*`;

    const allDoneMessage =
      "🎉 *All tasks completed!*\n\nGreat work everyone! Time to relax 😎🍹";

    const pendingMessage = [
      "📢 *Task Reminder*",
      "",
      deadlineLabel,
      `Deadline: ${new Date(status.currentWeek.deadline).toUTCString()}`,
      "",
      `📊 Progress: ${progressBar(status.completedCount, total)} ${status.completedCount}/${total}`,
      `🔴 *${remaining} tasks* still need to be done!`,
      "",
      status.notContributed.length > 0
        ? `💭 *Haven't contributed yet:*\n${status.notContributed.join(", ")}\n\n¡Hagámosle pues! 💪`
        : "¡Hagámosle pues! 💪",
    ].join("\n");

    return {
      ok: true as const,
      done: remaining <= 0,
      message: remaining <= 0 ? allDoneMessage : pendingMessage,
    };
  },
});

export const checkAndRollover = action({
  args: {},
  handler: async (ctx) => {
    const active = await ctx.runQuery(weeksGetActive, {});

    if (!active) {
      const createResult = await ctx.runMutation(weeksEnsureActive, {});
      return {
        ok: true as const,
        rolledOver: false,
        summaryMessage: null,
        newWeekAnnouncement: `🆕 *New Week Started!*\n\n📅 Week ${createResult.week.weekNumber}/${createResult.week.year}\n⏰ Deadline: ${new Date(createResult.week.deadline).toUTCString()}\n📋 Tasks to complete: ${Object.values(CATEGORY_AMOUNTS).reduce((acc, value) => acc + value, 0)}\n\nLet's make this week great! ¡Hagámosle pues! 💪`,
      };
    }

    if (Date.now() < active.deadline) {
      return {
        ok: true as const,
        rolledOver: false,
        summaryMessage: null,
        newWeekAnnouncement: null,
      };
    }

    const snapshot = await ctx.runQuery(statusGetWeekSnapshot, { weekId: active._id });
    if (!snapshot) {
      return {
        ok: false as const,
        error: "missing_snapshot",
      };
    }

    const sortedContributors = Object.entries(snapshot.contributions as Record<string, number>).sort(
      (a, b) => b[1] - a[1],
    );

    let summary = `📅 *Week ${snapshot.week.weekNumber}/${snapshot.week.year} Summary*\n\n`;
    if (snapshot.remaining <= 0) {
      summary += "🎉 *WEEK COMPLETE!* 🎉\n\n";
      summary += `All ${snapshot.total} tasks were completed! Amazing work everyone! 💪\n\n`;
    } else {
      const percent = snapshot.total > 0 ? Math.floor((snapshot.completedCount / snapshot.total) * 100) : 0;
      summary += `📊 *Progress:* ${snapshot.completedCount}/${snapshot.total} tasks (${percent}%)\n`;
      summary += `⚠️ ${snapshot.remaining} tasks were not completed.\n\n`;
    }

    if (sortedContributors.length > 0) {
      summary += "🌟 *Thank you to our contributors:*\n";
      for (const [name, count] of sortedContributors) {
        const emoji = count >= 5 ? "🏆" : count >= 3 ? "⭐" : "✅";
        summary += `${emoji} *${name}* - ${count} task${count === 1 ? "" : "s"}\n`;
      }
      summary += "\n_Thanks to you, the corridor is a better place!_ 🏠✨\n\n";
    }

    if (snapshot.nonContributors.length > 0) {
      summary += "💭 *We missed you this week:*\n";
      summary += `${snapshot.nonContributors.join(", ")}\n\n`;
      summary += "_We would love to see you participate next week! Is there any reason you couldn't contribute to the tasks? Feel free to reach out if you need help or have concerns._\n\n";
    }

    summary += "➡️ *New week starting now!* Let's keep our corridor clean! 🧹";

    await ctx.runMutation(weeksClose, { weekId: active._id });
    const createResult = await ctx.runMutation(weeksEnsureActive, {});

    return {
      ok: true as const,
      rolledOver: true,
      summaryMessage: summary,
      newWeekAnnouncement: `🆕 *New Week Started!*\n\n📅 Week ${createResult.week.weekNumber}/${createResult.week.year}\n⏰ Deadline: ${new Date(createResult.week.deadline).toUTCString()}\n📋 Tasks to complete: ${Object.values(CATEGORY_AMOUNTS).reduce((acc, value) => acc + value, 0)}\n\nLet's make this week great! ¡Hagámosle pues! 💪`,
    };
  },
});
