import { ConvexHttpClient } from "convex/browser";

export function createConvexClient() {
  const url = process.env.CONVEX_URL;
  if (!url) {
    throw new Error("Missing CONVEX_URL. Start local Convex with `bun run convex:dev`.");
  }
  return new ConvexHttpClient(url);
}
