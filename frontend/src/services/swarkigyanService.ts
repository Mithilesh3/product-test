import API from "./api";

export type SwarLanguage = "auto" | "hindi" | "english" | "hinglish";
export type SwarHistoryRole = "user" | "assistant";

export interface SwarHistoryMessage {
  role: SwarHistoryRole;
  content: string;
}

export interface SwarChatRequest {
  message: string;
  language_preference?: SwarLanguage;
  history?: SwarHistoryMessage[];
}

export interface SwarChatResponse {
  reply: string;
  language: "hindi" | "english" | "hinglish";
  safe_guard_applied: boolean;
  warning_count: number;
  account_blocked: boolean;
}

export const sendSwarChat = async (payload: SwarChatRequest): Promise<SwarChatResponse> => {
  const response = await API.post("/swarkigyan/chat", payload);
  return response.data;
};
