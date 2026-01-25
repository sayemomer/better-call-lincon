import { apiFetch } from "./client";

export type PromptCategory = {
  id: string;
  name: string;
  prompts: string[];
};

export type ChatPromptsResponse = {
  categories: PromptCategory[];
};

export type ChatRequest = {
  message: string;
  history?: { role: string; content: string }[];
};

export type ChatResponse = {
  reply: string;
};

export async function getChatPrompts(): Promise<ChatPromptsResponse> {
  return apiFetch<ChatPromptsResponse>("/api/v1/chat/prompts");
}

export async function sendChatMessage(
  message: string,
  history?: { role: string; content: string }[]
): Promise<ChatResponse> {
  return apiFetch<ChatResponse>("/api/v1/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history } satisfies ChatRequest),
  });
}
