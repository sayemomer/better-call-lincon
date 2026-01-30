import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { sendChatMessage } from "../api/chat";

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
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: uid(),
      role: "assistant",
      content: "Type your question below to get started. Ask about eligibility, CRS, deadlines, or anything else.",
    },
  ]);
  const [inputText, setInputText] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);

  const canSend = inputText.trim().length > 0 && !loading;

  useEffect(() => {
    listRef.current?.scrollTo({
      top: listRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  async function handleSend() {
    if (!canSend) return;

    const message = inputText.trim();
    const history = messages.map((m) => ({ role: m.role, content: m.content }));

    setChatError(null);
    setInputText("");
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
    } catch (e) {
      setChatError(e instanceof Error ? e.message : "Chat request failed.");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
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
                Ask anything about eligibility, CRS, deadlines, or next steps.
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

          {/* Open-ended input + Send */}
          <div className="mt-6 rounded-3xl border border-blue-200/40 bg-[#f4f8fc] p-4">
            {chatError && (
              <div className="mb-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
                {chatError}
              </div>
            )}
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <textarea
                ref={inputRef}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
                placeholder="Type your question…"
                rows={2}
                className="min-h-[2.5rem] flex-1 resize-y rounded-2xl border border-blue-200/40 bg-[#edf3f8] px-4 py-3 text-sm outline-none focus:border-blue-500 disabled:opacity-60"
              />
              <button
                onClick={handleSend}
                disabled={!canSend}
                className="rounded-2xl bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? "Sending…" : "Send"}
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
