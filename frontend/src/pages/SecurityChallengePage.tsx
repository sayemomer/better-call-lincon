import { useMemo, useState } from "react";

type Props = {
  questions: string[]; // the user's 3 saved questions
  onVerified: () => void;
  onCancel: () => void;
};

export default function SecurityChallengePage({ questions, onVerified, onCancel }: Props) {
  // pick a random question ONCE (useMemo ensures it won't change on re-renders)
  const picked = useMemo(() => {
    const idx = Math.floor(Math.random() * questions.length);
    return { idx, text: questions[idx] };
  }, [questions]);

  const [answer, setAnswer] = useState("");

  function handleVerify() {
    // MVP only: no real check (backend will verify)
    if (!answer.trim()) return alert("Please answer the security question.");
    onVerified();
  }

  return (
    <div className="min-h-screen text-white">
      <div className="absolute inset-0 -z-10 bg-gradient-to-br from-indigo-950 via-slate-950 to-emerald-950" />
      <div className="mx-auto flex min-h-screen max-w-lg items-center px-6">
        <div className="w-full rounded-3xl border border-white/10 bg-white/5 p-6 shadow-2xl backdrop-blur">
          <div className="text-sm text-white/70">Extra verification</div>
          <h1 className="mt-1 text-2xl font-semibold">Security Question</h1>

          <div className="mt-5 rounded-2xl border border-white/10 bg-black/20 p-4">
            <div className="text-xs text-white/60">Question</div>
            <div className="mt-2 text-sm font-medium">{picked.text}</div>
          </div>

          <div className="mt-4">
            <label className="text-sm text-white/80">Your answer</label>
            <input
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              className="mt-2 w-full rounded-2xl border border-white/10 bg-black/20 px-3 py-2 text-sm outline-none placeholder:text-white/35 focus:border-white/25"
              placeholder="Type your answer"
              autoComplete="off"
            />
          </div>

          <button
            type="button"
            onClick={handleVerify}
            className="mt-5 w-full rounded-2xl bg-gradient-to-r from-indigo-400 via-sky-400 to-emerald-300 px-3 py-2.5 text-sm font-semibold text-slate-950 hover:opacity-95"
          >
            Verify
          </button>

          <button
            type="button"
            onClick={onCancel}
            className="mt-3 w-full rounded-2xl border border-white/10 bg-black/20 px-3 py-2 text-sm text-white/80 hover:bg-black/30"
          >
            Back to login
          </button>

          <div className="mt-4 text-[11px] text-white/50">
            For the MVP, verification is UI-only. Next we’ll connect to backend.
          </div>
        </div>
      </div>
    </div>
  );
}