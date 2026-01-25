import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  uploadSignupDoc,
  getSignupDocStatus,
  isTerminalStatus,
  finalizeSignup,
  type SignupDocStatusResponse,
} from "../api/signupDoc";
import { setAccessToken } from "../api/auth";
import { signIn } from "../api/authApi";
import ExtractedSummary from "../components/ExtractedSummary";

type Mode = "signin" | "signup";

const POLL_INTERVAL_MS = 1500;

export default function AuthPage() {
  const navigate = useNavigate();

  const [mode, setMode] = useState<Mode>("signin");
  const isSignup = mode === "signup";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [passportFile, setPassportFile] = useState<File | null>(null);

  const [loading, setLoading] = useState(false);
  const [signinLoading, setSigninLoading] = useState(false);
  const [finalizeLoading, setFinalizeLoading] = useState(false);
  const [signupError, setSignupError] = useState<string | null>(null);
  const [signinError, setSigninError] = useState<string | null>(null);
  const [finalizeError, setFinalizeError] = useState<string | null>(null);
  const [signupResult, setSignupResult] = useState<SignupDocStatusResponse | null>(null);

  const inFinalizeStep = Boolean(
    isSignup && signupResult && !signupResult.is_error && signupResult.status !== "failed" && signupResult.needs_email_password
  );

  const title = useMemo(
    () =>
      inFinalizeStep ? "Complete your account" : isSignup ? "Create your account" : "Welcome back",
    [isSignup, inFinalizeStep]
  );

  async function pollUntilTerminal(jobId: string): Promise<SignupDocStatusResponse> {
    for (;;) {
      const data = await getSignupDocStatus(jobId);
      if (isTerminalStatus(data.status)) return data;
      await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS));
    }
  }

  async function handleSignupDoc() {
    if (!passportFile) {
      setSignupError("Please upload your passport (PDF or image).");
      return;
    }
    const allowed = ["application/pdf", "image/png", "image/jpeg"];
    if (!allowed.includes(passportFile.type)) {
      setSignupError("Upload a PDF or PNG/JPEG image.");
      return;
    }
    setSignupError(null);
    setSignupResult(null);
    setLoading(true);
    try {
      const { job_id } = await uploadSignupDoc(passportFile);
      const result = await pollUntilTerminal(job_id);
      setSignupResult(result);
      if (result.is_error || result.status === "failed") {
        setSignupError(
          result.reason || result.error || "Document is not a valid passport or processing failed."
        );
      }
    } catch (e) {
      setSignupError(e instanceof Error ? e.message : "Upload failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleFinalize() {
    const em = email.trim();
    const pw = password;
    if (!em) {
      setFinalizeError("Enter your email.");
      return;
    }
    if (pw.length < 8) {
      setFinalizeError("Password must be at least 8 characters.");
      return;
    }
    if (!signupResult?.job_id) return;
    setFinalizeError(null);
    setFinalizeLoading(true);
    try {
      const res = await finalizeSignup(signupResult.job_id, em, pw);
      setAccessToken(res.access_token);
      navigate("/home");
    } catch (e) {
      setFinalizeError(e instanceof Error ? e.message : "Could not complete signup.");
    } finally {
      setFinalizeLoading(false);
    }
  }

  async function handleSignIn() {
    const em = email.trim();
    if (!em) {
      setSigninError("Enter your email.");
      return;
    }
    if (!password) {
      setSigninError("Enter your password.");
      return;
    }
    setSigninError(null);
    setSigninLoading(true);
    try {
      await signIn(em, password);
      navigate("/home");
    } catch (e) {
      setSigninError(e instanceof Error ? e.message : "Sign in failed.");
    } finally {
      setSigninLoading(false);
    }
  }

  function handleSubmit() {
    if (inFinalizeStep) {
      handleFinalize();
      return;
    }
    if (isSignup) {
      handleSignupDoc();
      return;
    }
    handleSignIn();
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
                desc="Expiry reminders so you don't miss critical dates."
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

                {!inFinalizeStep && (
                  <div className="flex rounded-2xl border border-blue-200/40 bg-[#e6eef6] p-1 text-sm">
                    <button
                      onClick={() => {
                        setMode("signin");
                        setSignupError(null);
                        setSigninError(null);
                        setFinalizeError(null);
                        setSignupResult(null);
                      }}
                      className={`rounded-xl px-3 py-1.5 transition ${
                        mode === "signin"
                          ? "bg-blue-700 text-white shadow-sm"
                          : "text-slate-700 hover:bg-blue-200/50"
                      }`}
                    >
                      Sign in
                    </button>
                    <button
                      onClick={() => {
                        setMode("signup");
                        setSignupError(null);
                        setSigninError(null);
                        setFinalizeError(null);
                        setSignupResult(null);
                      }}
                      className={`rounded-xl px-3 py-1.5 transition ${
                        mode === "signup"
                          ? "bg-blue-700 text-white shadow-sm"
                          : "text-slate-700 hover:bg-blue-200/50"
                      }`}
                    >
                      Sign up
                    </button>
                  </div>
                )}
              </div>

              <p className="mt-3 text-sm text-slate-600">
                {inFinalizeStep
                  ? "Create your email and password to finish signup."
                  : isSignup
                    ? "Upload your passport. We validate it and extract your details."
                    : "Sign in to continue to your dashboard."}
              </p>

              {/* Form */}
              <div className="mt-6 space-y-4">
                {inFinalizeStep && signupResult && (
                  <>
                    <ExtractedSummary extracted={signupResult.extracted ?? {}} />
                    <Field label="Email">
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => {
                          setEmail(e.target.value);
                          setFinalizeError(null);
                        }}
                        className="w-full rounded-2xl border border-blue-200/40 bg-[#edf3f8] px-3 py-2 text-sm outline-none placeholder:text-slate-400 focus:border-blue-500"
                        placeholder="you@example.com"
                        autoComplete="email"
                      />
                    </Field>
                    <Field label="Password">
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => {
                          setPassword(e.target.value);
                          setFinalizeError(null);
                        }}
                        className="w-full rounded-2xl border border-blue-200/40 bg-[#edf3f8] px-3 py-2 text-sm outline-none placeholder:text-slate-400 focus:border-blue-500"
                        placeholder="At least 8 characters"
                        autoComplete="new-password"
                      />
                    </Field>
                    {finalizeError && (
                      <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                        {finalizeError}
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={handleSubmit}
                      disabled={finalizeLoading}
                      className="w-full rounded-2xl bg-blue-600 px-3 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
                    >
                      {finalizeLoading ? "Completing…" : "Complete signup"}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setSignupResult(null);
                        setFinalizeError(null);
                        setPassportFile(null);
                        if (fileInputRef.current) fileInputRef.current.value = "";
                      }}
                      className="w-full text-center text-sm text-slate-500 hover:text-slate-700 underline underline-offset-2"
                    >
                      Use a different passport
                    </button>
                  </>
                )}

                {!inFinalizeStep && !isSignup && (
                  <>
                    <Field label="Email">
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => {
                          setEmail(e.target.value);
                          setSigninError(null);
                        }}
                        className="w-full rounded-2xl border border-blue-200/40 bg-[#edf3f8] px-3 py-2 text-sm outline-none placeholder:text-slate-400 focus:border-blue-500"
                        placeholder="you@example.com"
                        autoComplete="email"
                      />
                    </Field>
                    <Field label="Password">
                      <input
                        type="password"
                        value={password}
                        onChange={(e) => {
                          setPassword(e.target.value);
                          setSigninError(null);
                        }}
                        className="w-full rounded-2xl border border-blue-200/40 bg-[#edf3f8] px-3 py-2 text-sm outline-none placeholder:text-slate-400 focus:border-blue-500"
                        placeholder="••••••••"
                        autoComplete="current-password"
                      />
                    </Field>
                    {signinError && (
                      <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                        {signinError}
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={handleSubmit}
                      disabled={signinLoading}
                      className="w-full rounded-2xl bg-blue-600 px-3 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
                    >
                      {signinLoading ? "Signing in…" : "Sign in"}
                    </button>
                  </>
                )}

                {isSignup && !inFinalizeStep && (
                  <>
                    <div className="rounded-2xl border border-blue-200/40 bg-[#e6eef6] p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-medium text-slate-900">Upload your passport</div>
                          <div className="mt-1 text-xs text-slate-600">
                            PDF or PNG/JPEG. We validate and extract your details.
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => fileInputRef.current?.click()}
                          disabled={loading}
                          className="rounded-xl bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
                        >
                          Choose file
                        </button>
                        <input
                          ref={fileInputRef}
                          type="file"
                          accept=".pdf,image/*"
                          className="hidden"
                          onChange={(e) => setPassportFile(e.target.files?.[0] ?? null)}
                        />
                      </div>
                      <div className="mt-3 text-xs text-slate-600">
                        {passportFile ? `Selected: ${passportFile.name}` : "No file selected"}
                      </div>
                    </div>
                    {signupError && (
                      <div className="rounded-2xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                        {signupError}
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={handleSubmit}
                      disabled={loading}
                      className="w-full rounded-2xl bg-blue-600 px-3 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-60"
                    >
                      {loading ? "Uploading & validating…" : "Create account"}
                    </button>
                  </>
                )}

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
