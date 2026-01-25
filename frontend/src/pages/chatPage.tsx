import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

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
      content:
        "Hi! Tell me your current status (student/work permit/PR) and what you need help with.",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const listRef = useRef<HTMLDivElement | null>(null);

  const canSend = useMemo(
    () => input.trim().length > 0 && !loading,
    [input, loading]
  );

  useEffect(() => {
    listRef.current?.scrollTo({
      top: listRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  async function handleSend() {
    if (!canSend) return;

    const userMessage: ChatMessage = {
      id: uid(),
      role: "user",
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    // fake reply
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: uid(),
          role: "assistant",
          content:
            "Thanks! Based on your message, I recommend reviewing your document expiry dates and checking eligibility criteria.",
        },
      ]);
      setLoading(false);
    }, 800);
  }

  return (
    <div className="min-h-screen bg-[#edf3f8] text-slate-800">
      {/* Fixed background */}
      <div className="fixed inset-0 -z-10 bg-[#e3edf6]" />

      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="rounded-3xl border border-blue-200/40 bg-[#f4f8fc] p-6 shadow-xl">

          {/* HEADER */}
          <div className="grid grid-cols-[auto,1fr,auto] items-center gap-4">
            <button
              onClick={() => navigate("/home")}
              className="bg-blue-600 text-white hover:bg-blue-700 rounded-2xl px-4 py-2 text-sm font-semibold shadow-sm"
            >
              ← Back
            </button>

            <div className="text-center">
              <div className="text-xs text-slate-500">AI Assistant</div>
              <h1 className="mt-1 text-2xl font-semibold text-slate-900">
                Chat with Immigration AI
              </h1>
              <p className="mt-2 text-sm text-slate-600">
                Ask about eligibility, deadlines, required documents, or next steps.
              </p>
            </div>

            <div />
          </div>

          {/* Chat window */}
          <div
            ref={listRef}
            className="mt-6 h-[60vh] overflow-y-auto rounded-3xl border border-blue-200/40 bg-[#edf3f8] p-4"
          >
            <div className="space-y-3">
              {messages.map((m) => (
                <ChatBubble key={m.id} role={m.role} content={m.content} />
              ))}
              {loading && (
                <div className="text-xs text-slate-500">AI is thinking...</div>
              )}
            </div>
          </div>

          {/* Input */}
          <div className="mt-6 rounded-3xl border border-blue-200/40 bg-[#f4f8fc] p-4">
            <div className="flex gap-3">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                rows={3}
                placeholder="Type your message..."
                className="flex-1 resize-none rounded-2xl border border-blue-200/40 bg-[#edf3f8] px-3 py-2 text-sm outline-none focus:border-blue-500"
              />

              <button
                onClick={handleSend}
                disabled={!canSend}
                className={`bg-blue-600 text-white hover:bg-blue-700 rounded-2xl px-5 py-2 font-semibold ${
                  !canSend ? "opacity-50 cursor-not-allowed" : ""
                }`}
              >
                Send
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