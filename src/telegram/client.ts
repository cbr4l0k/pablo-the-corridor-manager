import type {
  InlineKeyboardMarkup,
  TelegramUpdate,
} from "../types/telegram";
import { basename } from "node:path";
import { readFile } from "node:fs/promises";

type ApiResponse<T> = { ok: true; result: T } | { ok: false; description: string };

export class TelegramClient {
  constructor(private readonly token: string) {}

  private get baseUrl() {
    return `https://api.telegram.org/bot${this.token}`;
  }

  private async call<T>(method: string, payload: Record<string, unknown>): Promise<T> {
    const response = await fetch(`${this.baseUrl}/${method}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = (await response.json()) as ApiResponse<T>;
    if (!response.ok || !data.ok) {
      const errorText = "description" in data ? data.description : response.statusText;
      throw new Error(`Telegram API error (${method}): ${errorText}`);
    }
    return data.result;
  }

  getMe() {
    return this.call<{ id: number; username?: string }>("getMe", {});
  }

  getUpdates(offset: number, timeout: number): Promise<TelegramUpdate[]> {
    return this.call<TelegramUpdate[]>("getUpdates", {
      offset,
      timeout,
      allowed_updates: ["message", "callback_query"],
    });
  }

  sendMessage(params: {
    chatId: number;
    text: string;
    parseMode?: "Markdown";
    replyMarkup?: InlineKeyboardMarkup;
  }) {
    return this.call("sendMessage", {
      chat_id: params.chatId,
      text: params.text,
      parse_mode: params.parseMode,
      reply_markup: params.replyMarkup,
    });
  }

  editMessageText(params: {
    chatId: number;
    messageId: number;
    text: string;
    parseMode?: "Markdown";
    replyMarkup?: InlineKeyboardMarkup;
  }) {
    return this.call("editMessageText", {
      chat_id: params.chatId,
      message_id: params.messageId,
      text: params.text,
      parse_mode: params.parseMode,
      reply_markup: params.replyMarkup,
    });
  }

  answerCallbackQuery(params: { callbackQueryId: string; text?: string }) {
    return this.call("answerCallbackQuery", {
      callback_query_id: params.callbackQueryId,
      text: params.text,
    });
  }

  sendPhoto(params: { chatId: number; filePath: string; caption?: string; parseMode?: "Markdown" }) {
    const form = new FormData();
    form.append("chat_id", String(params.chatId));
    if (params.caption) form.append("caption", params.caption);
    if (params.parseMode) form.append("parse_mode", params.parseMode);
    return readFile(params.filePath).then((buffer) => {
      const blob = new Blob([buffer]);
      form.append("photo", blob, basename(params.filePath) || "map.jpg");
      return fetch(`${this.baseUrl}/sendPhoto`, {
        method: "POST",
        body: form,
      });
    }).then(async (response) => {
      const data = (await response.json()) as ApiResponse<unknown>;
      if (!response.ok || !data.ok) {
        const errorText = "description" in data ? data.description : response.statusText;
        throw new Error(`Telegram API error (sendPhoto): ${errorText}`);
      }
      return data.result;
    });
  }
}
