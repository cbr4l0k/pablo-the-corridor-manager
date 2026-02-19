export type CallbackPayload = {
  action: string;
  scope?: string;
  value?: string;
};

export function parseCallbackData(data: string): CallbackPayload {
  const [action, scope, value] = data.split(":");
  return { action, scope, value };
}
