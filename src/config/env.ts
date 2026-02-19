function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function optional(name: string, defaultValue: string): string {
  return process.env[name] ?? defaultValue;
}

export const env = {
  telegramBotToken: required("TELEGRAM_BOT_TOKEN"),
  telegramChatId: Number(required("TELEGRAM_CHAT_ID")),
  mapPath: optional("CORRIDOR_MAP_PATH", "media/corridor-overview.jpg"),
  pollingTimeoutSeconds: Number(optional("TELEGRAM_POLL_TIMEOUT_SECONDS", "30")),
  schedulerTickMs: Number(optional("SCHEDULER_TICK_MS", "60000")),
  tz: optional("APP_TIMEZONE", "Europe/Amsterdam"),
};
