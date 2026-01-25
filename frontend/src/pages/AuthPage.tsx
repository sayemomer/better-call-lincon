import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

type Mode = "signin" | "signup";

const SECURITY_QUESTIONS = [
  "What is the name of your first school?",
  "What city were you born in?",
  "What is your favorite food?",
  "What is your mother’s first name?",
  "What was the name of your first pet?",
  "What is the name of the street you grew up on?",
];

export default function AuthPage() {
  const navigate = useNavigate();

  const [mode, setMode] = useState<Mode>("signin");
  const isSignup = mode === "signup";

  // common fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // signup fields
  const [fullName, setFullName] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [passportFile, setPassportFile] = useState<File | null>(null);

  const [q1, setQ1] = useState(SECURITY_QUESTIONS[0]);
  const [q2, setQ2] = useState(SECURITY_QUESTIONS[1]);
  const [q3, setQ3] = useState(SECURITY_QUESTIONS[2]);

  const [a1, setA1] = useState("");
  const [a2, setA2] = useState("");
  const [a3, setA3] = useState("");

  const title = useMemo(
    () => (isSignup ? "Create your account" : "Welcome back"),
    [isSignup]
  );

  function handleSubmit() {
    if (!email.trim()) return alert("Enter email");
    if (!password.trim()) return alert("Enter password");

    if (isSignup) {
      if (!fullName.trim()) return alert("Enter full name");
      if (password.length < 6) return alert("Password must be 6+ characters");
      if (password !== confirmPassword) return alert("Passwords do not match");
      if (!passportFile) return alert("Please upload your passport (PDF or image).");
      if (!a1.trim() || !a2.trim() || !a3.trim())
        return alert("Please answer all 3 security questions.");

      // ✅ After signup go to dashboard
      navigate("/home");
      return;
    }

    // ✅ Login flow (for MVP): go home directly
    // (Later we’ll insert security-question challenge page)
    navigate("/home");
  }

  return (
    <div className="min-h-screen bg-[#edf3f8] text-slate-800">
      {/* Background (no white bottom ever) */}
      <div className="fixed inset-0 -z-20 bg-[#edf3f8]" />
      <div className="fixed inset-0 -z-10 opacity-100 [background:radial-gradient(circle_at_20%_15%,rgba(59,130,246,0.18),transparent_55%),radial-gradient(circle_at_85%_10%,rgba(16,185,129,0.10),transparent_60%),radial-gradient(circle_at_60%_90%,rgba(99,102,241,0.10),transparent_55%)]" />

      <div className="mx-auto max-w-6xl px-6 py-10 lg:py-16">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-2">
          {/* LEFT (sticky, does not move while right scrolls) */}
          <div className="lg:sticky lg:top-10 lg:h-[calc(100vh-5rem)]">
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-200/50 bg-[#e6eef6] px-3 py-1 text-xs text-slate-700">
              🇨🇦 AI Immigration Lawyer Agent • Hackathon MVP
            </div>

            <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-900">
              Your immigration pathway — simplified, guided, and tracked
            </h1>

            <p className="mt-4 max-w-xl text-slate-600">
              Track your pathway (Student → Work Permit → PR → Citizen), keep deadlines safe,
              and get smart suggestions based on your profile — all in one place.
            </p>

            {/* Feature cards */}
            <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <FeatureCard
                icon="🧠"
                title="Eligibility insights"
                desc="See what programs match your profile and what to improve next."
              />
              <FeatureCard
                icon="⏰"
                title="Deadline tracking"
                desc="Expiry reminders so you don’t miss critical dates."
              />
              <FeatureCard
                icon="📰"
                title="Policy updates"
                desc="Only show news relevant to your pathway and status."
              />
              <FeatureCard
                icon="📄"
                title="Docs + forms help"
                desc="Upload documents and get a checklist + guidance."
              />
            </div>

            <div className="mt-8 rounded-2xl border border-amber-200/60 bg-amber-100/60 p-4 text-sm text-amber-900">
              <div className="font-semibold">Important</div>
              <div className="mt-1 text-amber-900/80">
                This tool provides informational guidance only — it is <b>not</b> legal advice.
              </div>
            </div>

            {/* Decorative strip */}
            <div className="mt-10 hidden lg:block">
              <div className="h-1 w-40 rounded-full bg-gradient-to-r from-blue-600 via-sky-500 to-indigo-500" />
              <div className="mt-3 text-xs text-slate-500">
                Built for fast onboarding + secure recovery.
              </div>
            </div>
          </div>

          {/* RIGHT (scrolls if long) */}
          <div className="pb-10">
            <div className="mx-auto w-full max-w-md rounded-3xl border border-blue-200/40 bg-[#f4f8fc] p-6 shadow-2xl">
              {/* Toggle */}
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-slate-500">Authentication</div>
                  <h2 className="mt-1 text-2xl font-semibold text-slate-900">{title}</h2>
                </div>

                <div className="flex rounded-2xl border border-blue-200/40 bg-[#e6eef6] p-1 text-sm">
                  <button
                    onClick={() => setMode("signin")}
                    className={`rounded-xl px-3 py-1.5 transition ${
                      mode === "signin"
                        ? "bg-blue-700 text-white shadow-sm"
                        : "text-slate-700 hover:bg-blue-200/50"
                    }`}
                  >
                    Sign in
                  </button>
                  <button
                    onClick={() => setMode("signup")}
                    className={`rounded-xl px-3 py-1.5 transition ${
                      mode === "signup"
                        ? "bg-blue-700 text-white shadow-sm"
                        : "text-slate-700 hover:bg-blue-200/50"
                    }`}
                  >
                    Sign up
                  </button>
                </div>
              </div>

              <p className="mt-3 text-sm text-slate-600">
                {isSignup
                  ? "Create an account to save your profile, deadlines, and documents."
                  : "Sign in to continue to your dashboard."}
              </p>

              {/* Form */}
              <div className="mt-6 space-y-4">
                {isSignup && (
                  <Field label="Full name">
                    <input
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className="w-full rounded-2xl border border-blue-200/40 bg-[#edf3f8] px-3 py-2 text-sm outline-none placeholder:text-slate-400 focus:border-blue-500"
                      placeholder="Your full name"
                    />
                  </Field>
                )}

                <Field label="Email">
                  <input
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full rounded-2xl border border-blue-200/40 bg-[#edf3f8] px-3 py-2 text-sm outline-none placeholder:text-slate-400 focus:border-blue-500"
                    placeholder="you@example.com"
                  />
                </Field>

                <Field label="Password">
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full rounded-2xl border border-blue-200/40 bg-[#edf3f8] px-3 py-2 text-sm outline-none placeholder:text-slate-400 focus:border-blue-500"
                    placeholder="••••••••"
                  />
                </Field>

                {isSignup && (
                  <>
                    <Field label="Confirm password">
                      <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="w-full rounded-2xl border border-blue-200/40 bg-[#edf3f8] px-3 py-2 text-sm outline-none placeholder:text-slate-400 focus:border-blue-500"
                        placeholder="••••••••"
                      />
                    </Field>

                    {/* Passport upload */}
                    <div className="rounded-2xl border border-blue-200/40 bg-[#e6eef6] p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-medium text-slate-900">Upload your passport</div>
                          <div className="mt-1 text-xs text-slate-600">
                            PDF or image (MVP). Used later to prefill documents.
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={() => fileInputRef.current?.click()}
                          className="rounded-xl bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700"
                        >
                          Choose file
                        </button>

                        <input
                          ref={fileInputRef}
                          type="file"
                          accept=".pdf,image/*"
                          className="hidden"
                          onChange={(e) =>
                            setPassportFile(e.target.files?.[0] ?? null)
                          }
                        />
                      </div>

                      <div className="mt-3 text-xs text-slate-600">
                        {passportFile ? `Selected: ${passportFile.name}` : "No file selected"}
                      </div>
                    </div>

                    {/* Security questions */}
                    <div className="rounded-2xl border border-blue-200/40 bg-[#e6eef6] p-4">
                      <div className="font-medium text-slate-900">Security questions (3)</div>
                      <div className="mt-1 text-xs text-slate-600">
                        We’ll use these to verify you after login (randomly).
                      </div>

                      <div className="mt-4 space-y-4">
                        <SecurityBlock
                          label="Question #1"
                          valueQ={q1}
                          onQ={setQ1}
                          valueA={a1}
                          onA={setA1}
                        />
                        <SecurityBlock
                          label="Question #2"
                          valueQ={q2}
                          onQ={setQ2}
                          valueA={a2}
                          onA={setA2}
                        />
                        <SecurityBlock
                          label="Question #3"
                          valueQ={q3}
                          onQ={setQ3}
                          valueA={a3}
                          onA={setA3}
                        />
                      </div>
                    </div>
                  </>
                )}

                {/* CTA */}
                <button
                  type="button"
                  onClick={handleSubmit}
                  className="w-full rounded-2xl bg-blue-600 px-3 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
                >
                  {isSignup ? "Create account" : "Sign in"}
                </button>

                <div className="text-center text-xs text-slate-500">
                  By continuing, you agree to the MVP demo terms.
                </div>
              </div>
            </div>

            {/* right side extra padding so scroll feels good */}
            <div className="h-10" />
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-slate-600">{label}</div>
      <div className="mt-2">{children}</div>
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: string; title: string; desc: string }) {
  return (
    <div className="rounded-3xl border border-blue-200/40 bg-[#f4f8fc] p-4 shadow-xl">
      <div className="text-2xl">{icon}</div>
      <div className="mt-3 text-base font-semibold text-slate-900">{title}</div>
      <div className="mt-1 text-sm text-slate-600">{desc}</div>
    </div>
  );
}

function SecurityBlock({
  label,
  valueQ,
  onQ,
  valueA,
  onA,
}: {
  label: string;
  valueQ: string;
  onQ: (v: string) => void;
  valueA: string;
  onA: (v: string) => void;
}) {
  return (
    <div>
      <div className="text-xs text-slate-600">{label}</div>

      <select
        value={valueQ}
        onChange={(e) => onQ(e.target.value)}
        className="mt-2 w-full rounded-2xl border border-blue-200/40 bg-[#edf3f8] px-3 py-2 text-sm outline-none focus:border-blue-500"
      >
        {SECURITY_QUESTIONS.map((q) => (
          <option key={q} value={q}>
            {q}
          </option>
        ))}
      </select>

      <input
        value={valueA}
        onChange={(e) => onA(e.target.value)}
        className="mt-2 w-full rounded-2xl border border-blue-200/40 bg-[#edf3f8] px-3 py-2 text-sm outline-none placeholder:text-slate-400 focus:border-blue-500"
        placeholder="Your answer"
        autoComplete="off"
      />
    </div>
  );
}