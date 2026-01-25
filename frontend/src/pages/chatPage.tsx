import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getChatPrompts, sendChatMessage, type PromptCategory } from "../api/chat";

type Role = "user" | "assistant";

type ChatMessage = {
  id: string;
  role: Role;
  content: string;
};

function uid() {
  return Math.random().toString(16).slice(2);
}

export default function ChatPage() {
  const navigate = useNavigate();
  const [categories, setCategories] = useState<PromptCategory[]>([]);
  const [promptsLoading, setPromptsLoading] = useState(true);
  const [promptsError, setPromptsError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: uid(),
      role: "assistant",
      content: "Choose a question from the dropdown below to get started.",
    },
  ]);
  const [selectedPrompt, setSelectedPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);

  const canSend = useMemo(
    () => selectedPrompt.trim().length > 0 && !loading,
    [selectedPrompt, loading]
  );

  useEffect(() => {
    let ignore = false;
    setPromptsLoading(true);
    setPromptsError(null);
    getChatPrompts()
      .then((res) => { if (!ignore) setCategories(res.categories ?? []); })
      .catch((e) => {
        if (!ignore) setPromptsError(e instanceof Error ? e.message : "Could not load prompts.");
      })
      .finally(() => { if (!ignore) setPromptsLoading(false); });
    return () => { ignore = true; };
  }, []);

  useEffect(() => {
    listRef.current?.scrollTo({
      top: listRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  async function handleSend() {
    if (!canSend) return;

    const message = selectedPrompt.trim();
    const history = messages.map((m) => ({ role: m.role, content: m.content }));

    setChatError(null);
    setLoading(true);

    try {
      const res = await sendChatMessage(message, history);
      const userMsg: ChatMessage = { id: uid(), role: "user", content: message };
      const assistantMsg: ChatMessage = {
        id: uid(),
        role: "assistant",
        content: res.reply,
      };
      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setSelectedPrompt("");
    } catch (e) {
      setChatError(e instanceof Error ? e.message : "Chat request failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#edf3f8] text-slate-800">
      <div className="fixed inset-0 -z-10 bg-[#e3edf6]" />

      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="rounded-3xl border border-blue-200/40 bg-[#f4f8fc] p-6 shadow-xl">
          {/* HEADER */}
          <div className="grid grid-cols-[auto,1fr,auto] items-center gap-4">
            <button
              onClick={() => navigate("/home")}
              className="rounded-2xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-700"
            >
              ← Back
            </button>

            <div className="text-center">
              <div className="text-xs text-slate-500">AI Assistant</div>
              <h1 className="mt-1 text-2xl font-semibold text-slate-900">
                Chat with Immigration AI
              </h1>
              <p className="mt-2 text-sm text-slate-600">
                Select a question to ask about eligibility, CRS, deadlines, or next steps.
              </p>
            </div>

            <div />
          </div>

          {/* Chat window */}
          <div
            ref={listRef}
            className="mt-6 h-[50vh] overflow-y-auto rounded-3xl border border-blue-200/40 bg-[#edf3f8] p-4"
          >
            <div className="space-y-3">
              {messages.map((m) => (
                <ChatBubble key={m.id} role={m.role} content={m.content} />
              ))}
              {loading && (
                <div className="text-sm text-slate-500">Immigration AI is thinking…</div>
              )}
            </div>
          </div>

          {/* Prompts dropdown + Send */}
          <div className="mt-6 rounded-3xl border border-blue-200/40 bg-[#f4f8fc] p-4">
            {promptsError && (
              <div className="mb-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                {promptsError}
              </div>
            )}
            {chatError && (
              <div className="mb-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
                {chatError}
              </div>
            )}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <select
                value={selectedPrompt}
                onChange={(e) => setSelectedPrompt(e.target.value)}
                disabled={promptsLoading || loading}
                className="flex-1 rounded-2xl border border-blue-200/40 bg-[#edf3f8] px-4 py-3 text-sm outline-none focus:border-blue-500 disabled:opacity-60"
              >
                <option value="">Choose a question…</option>
                {categories.map((cat) => (
                  <optgroup key={cat.id} label={cat.name}>
                    {(cat.prompts ?? []).map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              <button
                onClick={handleSend}
                disabled={!canSend}
                className="rounded-2xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? "Sending…" : "Ask"}
              </button>
            </div>
            <div className="mt-3 text-xs text-slate-500">
              This tool provides informational guidance only — not legal advice.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatBubble({
  role,
  content,
}: {
  role: Role;
  content: string;
}) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-3xl border px-4 py-3 text-sm shadow-sm ${
          isUser
            ? "border-blue-200/40 bg-white text-slate-900"
            : "border-blue-200/40 bg-[#f4f8fc] text-slate-900"
        }`}
      >
        {content}
      </div>
    </div>
  );
}
