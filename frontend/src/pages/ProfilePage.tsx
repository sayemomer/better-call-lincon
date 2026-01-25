import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { signOut } from "../api/authApi";
import { getProfile, type ProfileOut } from "../api/profile";
import EducationSummary from "../components/EducationSummary";
import LanguageTestsSummary from "../components/LanguageTestsSummary";

function ProfileField({ label, value }: { label: string; value: string | null | undefined }) {
  const v = value?.trim();
  return (
    <div className="flex flex-wrap gap-x-2 py-2 border-b border-blue-200/40 last:border-0">
      <span className="text-sm font-medium text-slate-600 min-w-[140px]">{label}</span>
      <span className="text-sm text-slate-900">{v || "—"}</span>
    </div>
  );
}

function ProfileSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl bg-[#e8f1f9] border border-blue-300/30 p-6">
      <h3 className="text-lg font-semibold text-slate-900 mb-4">{title}</h3>
      <div className="space-y-0">{children}</div>
    </div>
  );
}

function JsonBlock({ label, data }: { label: string; data: unknown }) {
  const isEmpty = data == null || (typeof data === "object" && !Array.isArray(data) && Object.keys(data as object).length === 0);
  if (isEmpty) {
    return <ProfileField label={label} value={null} />;
  }
  return (
    <div className="py-2 border-b border-blue-200/40 last:border-0">
      <div className="text-sm font-medium text-slate-600 mb-1">{label}</div>
      <pre className="text-xs text-slate-700 bg-white/80 rounded-lg p-3 overflow-x-auto max-h-40 overflow-y-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

export default function ProfilePage() {
  const nav = useNavigate();
  const [profile, setProfile] = useState<ProfileOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    let ignore = false;
    setLoading(true);
    setError(null);
    getProfile()
      .then((p) => { if (!ignore) setProfile(p); })
      .catch((e) => { if (!ignore) setError(e instanceof Error ? e.message : "Could not load profile."); })
      .finally(() => { if (!ignore) setLoading(false); });
    return () => { ignore = true; };
  }, []);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await signOut();
      nav("/");
    } finally {
      setLoggingOut(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#dfeaf4] text-slate-800">
      <div className="flex min-h-screen">
        {/* SIDEBAR */}
        <aside className="w-64 bg-[#d4e3f1] border-r border-blue-300/40 p-6">
          <div className="flex items-center gap-3 mb-8">
            <div className="h-10 w-10 rounded-xl bg-blue-200/70 flex items-center justify-center font-bold text-blue-800">
              🇨🇦
            </div>
            <div>
              <div className="font-semibold text-slate-900">Immigration AI</div>
              <div className="text-xs text-slate-600">Hackathon Project</div>
            </div>
          </div>
          <div className="space-y-2">
            <button
              onClick={() => nav("/home")}
              className="w-full px-4 py-2 rounded-lg text-sm font-medium text-left text-slate-700 hover:bg-blue-200/60 transition"
            >
              Home
            </button>
            <button
              onClick={() => nav("/profile")}
              className="w-full px-4 py-2 rounded-lg text-sm font-medium text-left bg-blue-700 text-white shadow-sm"
            >
              Profile
            </button>
            <button
              onClick={() => nav("/chat")}
              className="w-full px-4 py-2 rounded-lg text-sm font-medium text-left text-slate-700 hover:bg-blue-200/60 transition"
            >
              Chat with immigration AI
            </button>
            <button
              onClick={() => nav("/about")}
              className="w-full px-4 py-2 rounded-lg text-sm font-medium text-left text-slate-700 hover:bg-blue-200/60 transition"
            >
              About Us
            </button>
          </div>
        </aside>

        {/* MAIN */}
        <div className="flex-1">
          <div className="bg-[#dde9f5] border-b border-blue-300/40 px-8 py-4 flex justify-between items-center">
            <div>
              <div className="text-xs text-slate-500">Profile</div>
              <div className="text-xl font-semibold text-slate-900">Your immigration profile</div>
            </div>
            <button
              onClick={handleLogout}
              disabled={loggingOut}
              className="px-4 py-2 rounded-lg border border-blue-300/60 text-blue-800 bg-blue-100/60 hover:bg-blue-200/60 text-sm disabled:opacity-60"
            >
              {loggingOut ? "Logging out…" : "Logout"}
            </button>
          </div>

          <main className="p-8 space-y-6">
            {loading ? (
              <div className="rounded-2xl bg-[#e8f1f9] border border-blue-300/30 p-8 animate-pulse">
                <div className="h-6 w-48 rounded bg-slate-200" />
                <div className="mt-4 space-y-3">
                  {[1, 2, 3, 4, 5, 6].map((i) => (
                    <div key={i} className="h-5 rounded bg-slate-200" />
                  ))}
                </div>
              </div>
            ) : error ? (
              <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-amber-800">
                {error}
              </div>
            ) : profile ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ProfileSection title="Basic information">
                  <ProfileField label="Status" value={profile.status ?? undefined} />
                  <ProfileField label="Given name" value={profile.given_name ?? undefined} />
                  <ProfileField label="Surname" value={profile.surname ?? undefined} />
                  <ProfileField label="Date of birth" value={profile.dob ?? undefined} />
                  <ProfileField label="Citizenship" value={profile.citizenship ?? undefined} />
                  <ProfileField label="Sex" value={profile.sex ?? undefined} />
                  <ProfileField label="Place of birth" value={profile.place_of_birth ?? undefined} />
                </ProfileSection>

                <ProfileSection title="Passport">
                  <ProfileField label="Passport number" value={profile.passport_number ?? undefined} />
                  <ProfileField label="Country code" value={profile.country_code ?? undefined} />
                  <ProfileField label="Personal number" value={profile.personal_number ?? undefined} />
                  <ProfileField label="Date of issue" value={profile.date_of_issue ?? undefined} />
                  <ProfileField label="Date of expiry" value={profile.date_of_expiry ?? undefined} />
                </ProfileSection>

                <ProfileSection title="Family">
                  <ProfileField label="Marital status" value={profile.marital_status ?? undefined} />
                  <ProfileField label="Father's name" value={profile.fathers_name ?? undefined} />
                  <ProfileField label="Mother's name" value={profile.mothers_name ?? undefined} />
                </ProfileSection>

                <ProfileSection title="Location in Canada">
                  <ProfileField label="Province" value={profile.province ?? undefined} />
                  <ProfileField label="City" value={profile.city ?? undefined} />
                  <ProfileField label="Arrival date" value={profile.arrival_date ?? undefined} />
                </ProfileSection>

                <div className="lg:col-span-2">
                  <ProfileSection title="Address">
                    <ProfileField label="Permanent address" value={profile.permanent_address ?? undefined} />
                  </ProfileSection>
                </div>

                <ProfileSection title="Education">
                  <div className="pt-1">
                    <div className="text-sm font-medium text-slate-600 mb-2">
                      Education (from documents)
                    </div>
                    <EducationSummary data={profile.education_json} />
                  </div>
                </ProfileSection>

                <ProfileSection title="Language">
                  <div className="pt-1">
                    <div className="text-sm font-medium text-slate-600 mb-2">
                      Language tests (from documents)
                    </div>
                    <LanguageTestsSummary data={profile.language_json} />
                  </div>
                </ProfileSection>

                <div className="lg:col-span-2">
                  <ProfileSection title="Work experience">
                    <JsonBlock label="Work (from documents)" data={profile.work_json} />
                  </ProfileSection>
                </div>
              </div>
            ) : null}
          </main>
        </div>
      </div>
    </div>
  );
}
