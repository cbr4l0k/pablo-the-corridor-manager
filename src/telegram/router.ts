import { existsSync } from "node:fs";
import { parseCallbackData } from "../domain/callbacks";
import { refs } from "../convex/refs";
import { CATEGORY_AMOUNTS, CATEGORY_EMOJIS, PRIVATE_ONLY_ACTIONS } from "../domain/constants";
import { createMainMenu, createCategoryMenu, createTaskMenu } from "./menus";
import type { TelegramClient } from "./client";
import type { TelegramCallbackQuery, TelegramMessage, TelegramUpdate } from "../types/telegram";
import type { ConvexHttpClient } from "convex/browser";

function isPrivateChat(message: TelegramMessage | undefined) {
  return message?.chat.type === "private";
}

function parseCommand(text: string): { command: string; args: string[] } {
  const [command, ...args] = text.trim().split(/\s+/);
  return { command: command.toLowerCase(), args };
}

export async function handleUpdate(params: {
  update: TelegramUpdate;
  telegram: TelegramClient;
  convex: ConvexHttpClient;
  groupChatId: number;
  mapPath: string;
}) {
  const { update, telegram, convex, groupChatId, mapPath } = params;

  if (update.message?.text?.startsWith("/")) {
    await handleCommand(update.message, params);
    return;
  }

  if (update.callback_query?.data) {
    await handleCallback(update.callback_query, params);
  }
}

async function handleCommand(
  message: TelegramMessage,
  params: { telegram: TelegramClient; convex: ConvexHttpClient; groupChatId: number; mapPath: string },
) {
  const { telegram, convex, groupChatId, mapPath } = params;
  const { command, args } = parseCommand(message.text ?? "");

  if (command === "/start") {
    const from = message.from;
    if (!from) return;

    const result = await convex.mutation(refs.people.registerIfMissing, {
      telegramId: BigInt(from.id) as unknown as bigint,
      name: from.first_name,
      username: from.username,
    });

    const intro = result.created
      ? `Bienvenido Mijo 😉! You're registered, ${from.first_name}!\n\n`
      : `👋 Quiubo papi, ${result.person?.name ?? from.first_name}!\n\n`;

    const suffix = isPrivateChat(message)
      ? "🔒 Private menu below (all features):"
      : "👥 Group menu below (public features only):";

    await telegram.sendMessage({
      chatId: message.chat.id,
      text: intro + suffix,
      replyMarkup: createMainMenu(isPrivateChat(message)),
    });
    return;
  }

  if (command === "/menu") {
    const text = isPrivateChat(message)
      ? "🤖 *Pablito's Corridor Manager*\n\n🔒 Choose an action:"
      : "🤖 *Pablito's Corridor Manager*\n\n👥 Public actions:";
    await telegram.sendMessage({
      chatId: message.chat.id,
      text,
      parseMode: "Markdown",
      replyMarkup: createMainMenu(isPrivateChat(message)),
    });
    return;
  }

  if (command === "/help") {
    const text = isPrivateChat(message)
      ? "🤖 *Pablito's Corridor Manager*\n\n*Interactive Menu:*\n/menu - Show button menu\n/start - Register & show menu\n\n*Commands:*\n/status - Full weekly status\n/tasks - List all tasks\n/mystats - Your detailed stats\n/optout <task> <reason> - Opt out\n/whooptedout - See opt-outs\n/map - Show corridor map\n\n💡 Use buttons for easy navigation!"
      : "🤖 *Pablito's Corridor Manager*\n\n*Group Commands:*\n/status - Weekly status\n/tasks - List all tasks\n/whooptedout - See opt-outs\n\n🔒 *For private actions:*\nMessage me privately to:\n• Complete tasks\n• Amend tasks\n• See your stats\n• View map\n• Opt out of tasks\n\n💡 Use buttons for quick access!";

    await telegram.sendMessage({ chatId: message.chat.id, text, parseMode: "Markdown" });
    return;
  }

  if (command === "/status") {
    const status = await convex.query(refs.status.getStatusDetailed, {});
    if (!status.ok) {
      await telegram.sendMessage({ chatId: message.chat.id, text: "❌ No active week found." });
      return;
    }

    let response = `📅 *Week ${status.currentWeek.weekNumber}/${status.currentWeek.year}*\n`;
    response += `⏰ Deadline: ${new Date(status.currentWeek.deadline).toUTCString()}\n\n`;
    response += "📈 *Progress by Category*\n";

    for (const category of Object.keys(status.byCategory).sort()) {
      const stats = status.byCategory[category];
      const total = CATEGORY_AMOUNTS[category] ?? 1;
      const progress = total > 0 ? Math.floor((stats.completed / total) * 10) : 0;
      const bar = "█".repeat(progress) + "░".repeat(10 - progress);
      const emoji = CATEGORY_EMOJIS[category] ?? "📦";
      response += `${emoji} ${capitalize(category)}: ${bar} ${stats.completed}/${total}\n`;
    }

    response += `\n📊 *Overall*: ${status.overallBar} ${status.completedCount}/${status.overallTotal}\n\n`;
    response += `✅ *Completed (${status.completedCount})*\n`;
    for (const item of status.completedTasks.slice(-5)) {
      response += `  • ${item.taskName} - ${item.personName ?? "Unknown"}\n`;
    }
    if (status.completedCount > 5) {
      response += `  ... and ${status.completedCount - 5} more\n`;
    }

    if (status.done) {
      response += "\n🎉 All tasks done! Time to relax! 😎🍹\n";
    }

    if (!status.done && status.notContributed.length > 0) {
      response += `\n¿Y entonces qué? 😡🔪\n💭 *Haven't contributed:* ${status.notContributed.join(", ")}`;
    }

    await telegram.sendMessage({ chatId: message.chat.id, text: response, parseMode: "Markdown" });
    return;
  }

  if (command === "/tasks") {
    const catalog = await convex.query(refs.tasks.listTaskCatalog, {});
    let response = "📋 *All Available Tasks*\n\n";

    for (const categoryRow of catalog) {
      const emoji = CATEGORY_EMOJIS[categoryRow.category] ?? "📦";
      response += `${emoji} *${capitalize(categoryRow.category)}* [Complete ${categoryRow.target}/week]\n`;
      for (const task of categoryRow.tasks) {
        const duration = task.estimatedDurationMinutes ? ` (${task.estimatedDurationMinutes}min)` : "";
        response += `  • ${task.name}${duration}\n`;
      }
      response += "\n";
    }

    await telegram.sendMessage({ chatId: message.chat.id, text: response, parseMode: "Markdown" });
    return;
  }

  if (command === "/mystats") {
    if (!isPrivateChat(message)) {
      await redirectToPrivate(message, telegram, "My Stats");
      return;
    }
    const from = message.from;
    if (!from) return;
    const stats = await convex.query(refs.tasks.getMyStats, {
      telegramId: BigInt(from.id) as unknown as bigint,
    });
    if (!stats.ok) {
      await telegram.sendMessage({ chatId: message.chat.id, text: "❌ You're not registered! Use /start first." });
      return;
    }
    let response = `📊 *Stats for ${stats.person.name}*\n\n`;
    if (stats.currentWeek) {
      response += `*This Week (Week ${stats.currentWeek.weekNumber}):*\n`;
      response += `Tasks completed: *${stats.weekTasks.length}*\n`;
      if (stats.weekTasks.length > 0) {
        response += "\nTasks:\n";
        for (const row of stats.weekTasks) response += `  • ${row.name}\n`;
      }
    } else {
      response += "No active week.\n";
    }

    response += `\n*All-Time:*\nTotal: *${stats.allTime}* tasks\n`;
    if (stats.optOutNames.length > 0) {
      response += "\n*Opted out of:*\n";
      for (const name of stats.optOutNames) response += `  • ${name}\n`;
    }

    await telegram.sendMessage({ chatId: message.chat.id, text: response, parseMode: "Markdown" });
    return;
  }

  if (command === "/map") {
    if (!isPrivateChat(message)) {
      await redirectToPrivate(message, telegram, "Map");
      return;
    }

    if (!existsSync(mapPath)) {
      await telegram.sendMessage({ chatId: message.chat.id, text: "❌ Map not found." });
      return;
    }

    await telegram.sendPhoto({
      chatId: message.chat.id,
      filePath: mapPath,
      caption: "🗺️ *Corridor Map*",
      parseMode: "Markdown",
    });
    return;
  }

  if (command === "/optout") {
    if (!isPrivateChat(message)) {
      await redirectToPrivate(message, telegram, "Opt Out");
      return;
    }

    if (args.length < 2) {
      await telegram.sendMessage({
        chatId: message.chat.id,
        text: "❌ Please specify task and reason!\n\nUsage: `/optout <task_name> <reason>`\nExample: `/optout Fridge 1 I have my own fridge`\nExample: `/optout Kitchen A I don't use communal kitchen`\n\nUse /tasks to see all available tasks.",
        parseMode: "Markdown",
      });
      return;
    }

    const from = message.from;
    if (!from) return;

    const taskQuery = args[0];
    const reason = args.slice(1).join(" ");

    const result = await convex.mutation(refs.optouts.createOptOut, {
      telegramId: BigInt(from.id) as unknown as bigint,
      taskQuery,
      reason,
    });

    if (!result.ok) {
      if (result.error === "not_registered") {
        await telegram.sendMessage({
          chatId: message.chat.id,
          text: "❌ You're not registered! Use /start to register first.",
        });
      } else if (result.error === "task_not_found") {
        await telegram.sendMessage({
          chatId: message.chat.id,
          text: `❌ Task matching '${result.taskQuery}' not found.\n\nUse /tasks to see all available tasks.`,
        });
      } else {
        await telegram.sendMessage({
          chatId: message.chat.id,
          text: `⚠️ You're already opted out of '${result.taskName}'.\nCurrent reason: ${result.reason}\n\nContact an administrator if you want to change the reason or opt back in.`,
        });
      }
      return;
    }

    await telegram.sendMessage({
      chatId: message.chat.id,
      text: `✅ Opt-out successful!\n\nYou've opted out of: *${result.taskName}*\nReason: ${result.reason}\n\nYou won't be expected to complete this task.\nUse \`/whooptedout ${result.taskName}\` to see all opt-outs for this task.`,
      parseMode: "Markdown",
    });

    await telegram.sendMessage({
      chatId: groupChatId,
      text: `ℹ️ ${result.personName} opted out of *${result.taskName}*\nReason: ${result.reason}`,
      parseMode: "Markdown",
    });
    return;
  }

  if (command === "/whooptedout") {
    const queryText = args.length ? args.join(" ") : undefined;
    const result = await convex.query(refs.optouts.listWhoOptedOut, { taskQuery: queryText });

    if (result.rows.length === 0) {
      await telegram.sendMessage({
        chatId: message.chat.id,
        text: queryText ? `ℹ️ No opt-outs for *${queryText}*` : "ℹ️ No opt-outs yet!",
        parseMode: queryText ? "Markdown" : undefined,
      });
      return;
    }

    if (!queryText) {
      const byTask: Record<string, string[]> = {};
      for (const row of result.rows) {
        byTask[row.taskName] ??= [];
        byTask[row.taskName].push(`${row.personName} (${row.reason})`);
      }

      let response = "📋 *Current Opt-Outs*\n\n";
      for (const taskName of Object.keys(byTask).sort()) {
        response += `*${taskName}:*\n`;
        for (const person of byTask[taskName]) response += `  • ${person}\n`;
        response += "\n";
      }

      await telegram.sendMessage({ chatId: message.chat.id, text: response, parseMode: "Markdown" });
      return;
    }

    let response = `📋 *Opt-Outs for ${queryText}*\n\n`;
    for (const row of result.rows) {
      response += `• ${row.personName}\n  Reason: ${row.reason}\n\n`;
    }
    await telegram.sendMessage({ chatId: message.chat.id, text: response, parseMode: "Markdown" });
  }
}

async function handleCallback(
  query: TelegramCallbackQuery,
  params: { telegram: TelegramClient; convex: ConvexHttpClient; mapPath: string; groupChatId: number },
) {
  const { telegram, convex, mapPath, groupChatId } = params;
  if (!query.message || !query.data) return;

  await telegram.answerCallbackQuery({ callbackQueryId: query.id });

  const parsed = parseCallbackData(query.data);
  const privateChat = isPrivateChat(query.message);

  if (PRIVATE_ONLY_ACTIONS.has(parsed.action) && !privateChat) {
    await redirectCallbackToPrivate(query, telegram, capitalize(parsed.action));
    return;
  }

  if (parsed.action === "menu") {
    const text = privateChat
      ? "🤖 *Pablito's Corridor Manager*\n\n🔒 Private Menu - Choose an action:"
      : "🤖 *Pablito's Corridor Manager*\n\n👥 Group Menu - Public actions only:";

    await telegram.editMessageText({
      chatId: query.message.chat.id,
      messageId: query.message.message_id,
      text,
      parseMode: "Markdown",
      replyMarkup: createMainMenu(privateChat),
    });
    return;
  }

  if (parsed.action === "help") {
    const text = privateChat
      ? "🤖 *Pablito's Corridor Manager*\n\n🔒 *Private Chat Commands:*\n/menu - Show full menu\n/status - Weekly status\n/tasks - List all tasks\n/mystats - Your stats\n/map - Corridor map\n/optout <task> <reason> - Opt out\n/whooptedout - See opt-outs\n\n💡 Use buttons for easy task management!"
      : "🤖 *Pablito's Corridor Manager*\n\n👥 *Group Chat Commands:*\n/status - Weekly status\n/tasks - List all tasks\n/whooptedout - See opt-outs\n\n🔒 *Private Actions:*\nTo complete tasks, amend, or see your stats,\nmessage me privately\n\n💡 Use buttons for quick access!";

    await telegram.editMessageText({
      chatId: query.message.chat.id,
      messageId: query.message.message_id,
      text,
      parseMode: "Markdown",
      replyMarkup: { inline_keyboard: [[{ text: "« Back to Menu", callback_data: "menu" }]] },
    });
    return;
  }

  if (parsed.action === "status") {
    const status = await convex.query(refs.status.getStatusSummary, {});
    if (!status.ok) {
      await telegram.editMessageText({
        chatId: query.message.chat.id,
        messageId: query.message.message_id,
        text: "❌ No active week found.",
      });
      return;
    }

    const text = `📅 *Week ${status.currentWeek.weekNumber}/${status.currentWeek.year}*\n⏰ Deadline: ${new Date(status.currentWeek.deadline).toUTCString()}\n\n📊 Progress: ${status.overallBar} ${status.completedCount}/${status.total}\n\n💡 Use /status for detailed view`;

    await telegram.editMessageText({
      chatId: query.message.chat.id,
      messageId: query.message.message_id,
      text,
      parseMode: "Markdown",
      replyMarkup: { inline_keyboard: [[{ text: "« Back to Menu", callback_data: "menu" }]] },
    });
    return;
  }

  if (parsed.action === "tasks") {
    const catalog = await convex.query(refs.tasks.listTaskCatalog, {});
    let text = "📋 *All Available Tasks*\n\n";
    for (const categoryRow of catalog) {
      const emoji = CATEGORY_EMOJIS[categoryRow.category] ?? "📦";
      text += `${emoji} *${capitalize(categoryRow.category)}* [${categoryRow.target}/week]\n`;
      for (const task of categoryRow.tasks.slice(0, 3)) {
        const duration = task.estimatedDurationMinutes ? ` (${task.estimatedDurationMinutes}min)` : "";
        text += `  • ${task.name}${duration}\n`;
      }
      if (categoryRow.tasks.length > 3) text += `  ... and ${categoryRow.tasks.length - 3} more\n`;
      text += "\n";
    }
    text += "💡 Use /tasks for complete list";

    await telegram.editMessageText({
      chatId: query.message.chat.id,
      messageId: query.message.message_id,
      text,
      parseMode: "Markdown",
      replyMarkup: { inline_keyboard: [[{ text: "« Back to Menu", callback_data: "menu" }]] },
    });
    return;
  }

  if (parsed.action === "mystats") {
    const stats = await convex.query(refs.tasks.getMyStats, {
      telegramId: BigInt(query.from.id) as unknown as bigint,
    });
    if (!stats.ok) {
      await telegram.editMessageText({
        chatId: query.message.chat.id,
        messageId: query.message.message_id,
        text: "❌ You're not registered!",
      });
      return;
    }

    const weekCount = stats.weekTasks.length;
    const text = `📊 *Stats for ${stats.person.name}*\n\nThis week: *${weekCount}* tasks\nAll-time: *${stats.allTime}* tasks\n\n💡 Use /mystats for detailed view`;

    await telegram.editMessageText({
      chatId: query.message.chat.id,
      messageId: query.message.message_id,
      text,
      parseMode: "Markdown",
      replyMarkup: { inline_keyboard: [[{ text: "« Back to Menu", callback_data: "menu" }]] },
    });
    return;
  }

  if (parsed.action === "map") {
    if (existsSync(mapPath)) {
      await telegram.sendPhoto({
        chatId: query.message.chat.id,
        filePath: mapPath,
        caption: "🗺️ *Corridor Map*",
        parseMode: "Markdown",
      });
      await telegram.editMessageText({
        chatId: query.message.chat.id,
        messageId: query.message.message_id,
        text: "Map sent above! ⬆️",
        replyMarkup: { inline_keyboard: [[{ text: "« Back to Menu", callback_data: "menu" }]] },
      });
    } else {
      await telegram.editMessageText({
        chatId: query.message.chat.id,
        messageId: query.message.message_id,
        text: "❌ Map not found.",
        replyMarkup: { inline_keyboard: [[{ text: "« Back to Menu", callback_data: "menu" }]] },
      });
    }
    return;
  }

  if (parsed.action === "whooptedout") {
    const result = await convex.query(refs.optouts.listWhoOptedOut, {});
    let text = "ℹ️ No one has opted out yet!";
    if (result.rows.length > 0) {
      const byTask: Record<string, string[]> = {};
      for (const row of result.rows) {
        byTask[row.taskName] ??= [];
        byTask[row.taskName].push(row.personName);
      }

      text = "📋 *Current Opt-Outs*\n\n";
      const first = Object.keys(byTask).sort().slice(0, 5);
      for (const taskName of first) {
        text += `*${taskName}:* ${byTask[taskName].join(", ")}\n`;
      }
      if (Object.keys(byTask).length > 5) {
        text += `\n... and ${Object.keys(byTask).length - 5} more tasks\n`;
      }
      text += "\n💡 Use /whooptedout for full list";
    }

    await telegram.editMessageText({
      chatId: query.message.chat.id,
      messageId: query.message.message_id,
      text,
      parseMode: "Markdown",
      replyMarkup: { inline_keyboard: [[{ text: "« Back to Menu", callback_data: "menu" }]] },
    });
    return;
  }

  await handleTaskFlow(query, parsed, params);
}

async function handleTaskFlow(
  query: TelegramCallbackQuery,
  parsed: ReturnType<typeof parseCallbackData>,
  params: { telegram: TelegramClient; convex: ConvexHttpClient; groupChatId: number },
) {
  const { telegram, convex, groupChatId } = params;
  if (!query.message) return;

  if ((parsed.action === "complete" || parsed.action === "amend" || parsed.action === "ask") && parsed.scope === "categories") {
    const action = parsed.action as "complete" | "amend" | "ask";
    const data = await convex.query(refs.tasks.getCategoryProgress, { action });
    if (!data.currentWeek) {
      const noDataText = action === "amend" ? "ℹ️ No completed tasks to amend." : "❌ No active week found.";
      await telegram.editMessageText({
        chatId: query.message.chat.id,
        messageId: query.message.message_id,
        text: noDataText,
      });
      return;
    }

    const title = action === "complete" ? "✅ *Complete a Task*" : action === "amend" ? "❌ *Amend a Task*" : "❓ *Ask Instructions*";
    await telegram.editMessageText({
      chatId: query.message.chat.id,
      messageId: query.message.message_id,
      text: `${title}\n\nSelect a category:`,
      parseMode: "Markdown",
      replyMarkup: createCategoryMenu(action, data.categories),
    });
    return;
  }

  if ((parsed.action === "complete" || parsed.action === "amend" || parsed.action === "ask") && parsed.scope === "category" && parsed.value) {
    const action = parsed.action as "complete" | "amend" | "ask";
    const category = parsed.value;
    const data = await convex.query(refs.tasks.getTasksByCategory, { action, category });

    if (data.tasks.length === 0) {
      const emptyText =
        action === "complete"
          ? `ℹ️ No pending tasks in ${category}!`
          : action === "amend"
            ? `ℹ️ No completed tasks in ${category} to amend!`
            : `ℹ️ No tasks in ${category}!`;

      await telegram.editMessageText({
        chatId: query.message.chat.id,
        messageId: query.message.message_id,
        text: emptyText,
        replyMarkup: {
          inline_keyboard: [[{ text: "« Back", callback_data: `${action}:categories` }]],
        },
      });
      return;
    }

    const emoji = CATEGORY_EMOJIS[category] ?? "📦";
    const title = action === "complete" ? "✅ *Complete a Task*" : action === "amend" ? "❌ *Amend a Task*" : "❓ *Ask Instructions*";

    await telegram.editMessageText({
      chatId: query.message.chat.id,
      messageId: query.message.message_id,
      text: `${title}\n\n${emoji} ${capitalize(category)} - Select a task:`,
      parseMode: "Markdown",
      replyMarkup: createTaskMenu(action, `${action}:categories`, data.tasks),
    });
    return;
  }

  if ((parsed.action === "complete" || parsed.action === "amend" || parsed.action === "ask") && parsed.scope === "task" && parsed.value) {
    if (parsed.action === "ask") {
      const details = await convex.query(refs.tasks.getTaskInstructions, {
        taskInstanceId: parsed.value as any,
      });

      if (!details) {
        await telegram.editMessageText({
          chatId: query.message!.chat.id,
          messageId: query.message!.message_id,
          text: "❌ Task not found.",
        });
        return;
      }

      let text = `📋 *${details.taskType.name}*\n\n`;
      if (details.taskType.description) text += `${details.taskType.description}\n\n`;
      if (details.taskType.instructions) text += `*How to do it:*\n${details.taskType.instructions}\n\n`;
      if (details.taskType.location) text += `📍 Location: ${details.taskType.location}\n`;
      if (details.taskType.estimatedDurationMinutes) text += `⏱ Time: ${details.taskType.estimatedDurationMinutes} min\n`;

      await telegram.editMessageText({
        chatId: query.message!.chat.id,
        messageId: query.message!.message_id,
        text,
        parseMode: "Markdown",
        replyMarkup: {
          inline_keyboard: [
            [{ text: "❓ Ask Another", callback_data: "ask:categories" }],
            [{ text: "« Back to Menu", callback_data: "menu" }],
          ],
        },
      });
      return;
    }

    if (parsed.action === "complete") {
      const result = await convex.mutation(refs.tasks.completeTask, {
        taskInstanceId: parsed.value as any,
        telegramId: BigInt(query.from.id) as unknown as bigint,
        messageId: BigInt(query.message!.message_id) as unknown as bigint,
      });

      if (!result.ok) {
        if (result.error === "not_registered") {
          await telegram.editMessageText({
            chatId: query.message!.chat.id,
            messageId: query.message!.message_id,
            text: "❌ You're not registered! Use /start first.",
          });
          return;
        }
        if (result.error === "opted_out") {
          await telegram.editMessageText({
            chatId: query.message!.chat.id,
            messageId: query.message!.message_id,
            text: `⚠️ You've opted out of '${result.taskName}'.\nReason: ${result.reason}`,
            replyMarkup: { inline_keyboard: [[{ text: "« Back to Menu", callback_data: "menu" }]] },
          });
          return;
        }

        await telegram.editMessageText({
          chatId: query.message!.chat.id,
          messageId: query.message!.message_id,
          text: "❌ Task not found or already completed.",
        });
        return;
      }

      const text = `Eso es lo que nececitamos mijo!\n✅ *Great job, ${result.personName}!*\n\nTask completed: *${result.taskName}*\nYour tasks this week: *${result.personalCount}*\n📊 Remaining: *${result.remaining}*`;

      await telegram.editMessageText({
        chatId: query.message!.chat.id,
        messageId: query.message!.message_id,
        text,
        parseMode: "Markdown",
        replyMarkup: {
          inline_keyboard: [
            [{ text: "✅ Complete Another", callback_data: "complete:categories" }],
            [{ text: "« Back to Menu", callback_data: "menu" }],
          ],
        },
      });

      const groupMessage =
        result.remaining <= 0
          ? `🎉🎉🎉 ¡Mis amores! ${result.personName} Week Done! *${result.taskName}*!\nTime to chill 😎🍹`
          : `✅ ${result.personName} completed: *${result.taskName}*\n📊 ${result.remaining} remaining, hagamole pues!`;

      await telegram.sendMessage({ chatId: groupChatId, text: groupMessage, parseMode: "Markdown" });
      return;
    }

    if (parsed.action === "amend") {
      const result = await convex.mutation(refs.tasks.amendTask, {
        taskInstanceId: parsed.value as any,
        telegramId: BigInt(query.from.id) as unknown as bigint,
        messageId: BigInt(query.message!.message_id) as unknown as bigint,
      });

      if (!result.ok) {
        const message = result.error === "not_registered" ? "❌ You're not registered!" : "❌ Task not found or not completed.";
        await telegram.editMessageText({
          chatId: query.message!.chat.id,
          messageId: query.message!.message_id,
          text: message,
        });
        return;
      }

      await telegram.editMessageText({
        chatId: query.message!.chat.id,
        messageId: query.message!.message_id,
        text: `✅ Task amended!\n\n*${result.taskName}* is now pending.\nWas completed by: ${result.originalCompleter}\nAmended by: ${result.amendedBy}`,
        parseMode: "Markdown",
        replyMarkup: {
          inline_keyboard: [
            [{ text: "❌ Amend Another", callback_data: "amend:categories" }],
            [{ text: "« Back to Menu", callback_data: "menu" }],
          ],
        },
      });

      await telegram.sendMessage({
        chatId: groupChatId,
        text: `⚠️ ${result.amendedBy} amended *${result.taskName}*\n(was completed by ${result.originalCompleter})`,
        parseMode: "Markdown",
      });
      return;
    }
  }

  if (parsed.action === "optout") {
    await telegram.editMessageText({
      chatId: query.message.chat.id,
      messageId: query.message.message_id,
      text: "🚫 *Opt Out of a Task*\n\nTo opt out, use this command:\n`/optout <task> <reason>`\n\n*Example:*\n`/optout Fridge 1 I have my own fridge`\n\nOr use `/whooptedout` to see current opt-outs.",
      parseMode: "Markdown",
      replyMarkup: { inline_keyboard: [[{ text: "« Back to Menu", callback_data: "menu" }]] },
    });
  }
}

async function redirectToPrivate(message: TelegramMessage, telegram: TelegramClient, actionName: string) {
  const me = await telegram.getMe();
  const text = `🔒 *${actionName} is only available in private chat!*\n\nClick the button below to open private chat with me:`;
  await telegram.sendMessage({
    chatId: message.chat.id,
    text,
    parseMode: "Markdown",
    replyMarkup: {
      inline_keyboard: [[{ text: "💬 Open Private Chat", url: `https://t.me/${me.username ?? ""}` }]],
    },
  });
}

async function redirectCallbackToPrivate(
  query: TelegramCallbackQuery,
  telegram: TelegramClient,
  actionName: string,
) {
  if (!query.message) return;
  const me = await telegram.getMe();
  await telegram.answerCallbackQuery({
    callbackQueryId: query.id,
    text: "This action requires private chat!",
  });

  await telegram.editMessageText({
    chatId: query.message.chat.id,
    messageId: query.message.message_id,
    text: `🔒 *${actionName} is only available in private chat!*\n\nClick the button below to open private chat with me:`,
    parseMode: "Markdown",
    replyMarkup: {
      inline_keyboard: [[{ text: "💬 Open Private Chat", url: `https://t.me/${me.username ?? ""}` }]],
    },
  });
}

function capitalize(value: string): string {
  return value.length ? value[0].toUpperCase() + value.slice(1) : value;
}
