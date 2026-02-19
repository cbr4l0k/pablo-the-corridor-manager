import { env } from "./config/env";
import { createConvexClient } from "./convex/client";
import { refs } from "./convex/refs";
import { startSchedulers } from "./jobs/scheduler";
import { TelegramClient } from "./telegram/client";
import { handleUpdate } from "./telegram/router";

async function main() {
  const convex = createConvexClient();
  const telegram = new TelegramClient(env.telegramBotToken);

  await convex.mutation(refs.weeks.ensureActiveWeek, {});

  startSchedulers({
    convex,
    telegram,
    groupChatId: env.telegramChatId,
    tickMs: env.schedulerTickMs,
  });

  let offset = 0;
  while (true) {
    try {
      const updates = await telegram.getUpdates(offset, env.pollingTimeoutSeconds);
      for (const update of updates) {
        offset = update.update_id + 1;
        await handleUpdate({
          update,
          telegram,
          convex,
          groupChatId: env.telegramChatId,
          mapPath: env.mapPath,
        });
      }
    } catch (error) {
      console.error("Polling loop error", error);
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
