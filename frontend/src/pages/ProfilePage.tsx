import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { signOut } from "../api/authApi";
import { getProfile, updateProfile, type ProfileOut, type ProfileUpdate } from "../api/profile";
import EducationSummary from "../components/EducationSummary";
import LanguageTestsSummary from "../components/LanguageTestsSummary";

function ProfileField({ 
  label, 
  value, 
  editing, 
  onChange 
}: { 
  label: string; 
  value: string | null | undefined;
  editing?: boolean;
  onChange?: (value: string) => void;
}) {
  const v = value?.trim();
  if (editing && onChange !== undefined) {
    return (
      <div className="flex flex-wrap gap-x-2 py-2 border-b border-blue-200/40 last:border-0">
        <label className="text-sm font-medium text-slate-600 min-w-[140px]">{label}</label>
        <input
          type="text"
          value={v || ""}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 text-sm text-slate-900 px-2 py-1 border border-blue-300/60 rounded bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="—"
        />
      </div>
    );
  }
  return (
    <div className="flex flex-wrap gap-x-2 py-2 border-b border-blue-200/40 last:border-0">
      <span className="text-sm font-medium text-slate-600 min-w-[140px]">{label}</span>
      <span className="text-sm text-slate-900">{v || "—"}</span>
    </div>
  );
}

function ProfileDateField({ 
  label, 
  value, 
  editing, 
  onChange 
}: { 
  label: string; 
  value: string | null | undefined;
  editing?: boolean;
  onChange?: (value: string) => void;
}) {
  const v = value?.trim();
  if (editing && onChange !== undefined) {
    return (
      <div className="flex flex-wrap gap-x-2 py-2 border-b border-blue-200/40 last:border-0">
        <label className="text-sm font-medium text-slate-600 min-w-[140px]">{label}</label>
        <input
          type="date"
          value={v || ""}
          onChange={(e) => onChange(e.target.value)}
          className="flex-1 text-sm text-slate-900 px-2 py-1 border border-blue-300/60 rounded bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </div>
    );
  }
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
  editing,
  onEdit,
  onSave,
  onCancel,
}: {
  title: string;
  children: React.ReactNode;
  editing?: boolean;
  onEdit?: () => void;
  onSave?: () => void;
  onCancel?: () => void;
}) {
  return (
    <div className="rounded-2xl bg-[#e8f1f9] border border-blue-300/30 p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
        {!editing && onEdit && (
          <button
            onClick={onEdit}
            className="px-3 py-1 text-sm text-blue-700 bg-blue-100/60 hover:bg-blue-200/60 rounded-lg border border-blue-300/60 transition"
          >
            Edit
          </button>
        )}
        {editing && (
          <div className="flex gap-2">
            <button
              onClick={onSave}
              className="px-3 py-1 text-sm text-white bg-blue-700 hover:bg-blue-800 rounded-lg transition"
            >
              Save
            </button>
            <button
              onClick={onCancel}
              className="px-3 py-1 text-sm text-slate-700 bg-slate-200 hover:bg-slate-300 rounded-lg transition"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
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

type SectionKey = 
  | "basic"
  | "passport"
  | "family"
  | "location"
  | "address";

export default function ProfilePage() {
  const nav = useNavigate();
  const [profile, setProfile] = useState<ProfileOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);
  const [editingSection, setEditingSection] = useState<SectionKey | null>(null);
  const [editData, setEditData] = useState<Partial<ProfileOut>>({});
  const [saving, setSaving] = useState(false);

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

  function startEditing(section: SectionKey) {
    setEditingSection(section);
    setEditData(profile ? { ...profile } : {});
  }

  function cancelEditing() {
    setEditingSection(null);
    setEditData({});
  }

  async function saveSection(section: SectionKey) {
    if (!profile) return;
    
    setSaving(true);
    setError(null);
    
    try {
      const updates: ProfileUpdate = {};
      
      // Helper to normalize empty strings to null
      const normalize = (value: string | null | undefined): string | null | undefined => {
        if (value === undefined) return undefined;
        return value?.trim() || null;
      };
      
      // Map section fields to update
      switch (section) {
        case "basic":
          if (editData.status !== undefined) updates.status = normalize(editData.status);
          if (editData.given_name !== undefined) updates.given_name = normalize(editData.given_name);
          if (editData.surname !== undefined) updates.surname = normalize(editData.surname);
          if (editData.dob !== undefined) updates.dob = normalize(editData.dob);
          if (editData.citizenship !== undefined) updates.citizenship = normalize(editData.citizenship);
          if (editData.sex !== undefined) updates.sex = normalize(editData.sex);
          if (editData.place_of_birth !== undefined) updates.place_of_birth = normalize(editData.place_of_birth);
          break;
        case "passport":
          if (editData.passport_number !== undefined) updates.passport_number = normalize(editData.passport_number);
          if (editData.country_code !== undefined) updates.country_code = normalize(editData.country_code);
          if (editData.personal_number !== undefined) updates.personal_number = normalize(editData.personal_number);
          if (editData.date_of_issue !== undefined) updates.date_of_issue = normalize(editData.date_of_issue);
          if (editData.date_of_expiry !== undefined) updates.date_of_expiry = normalize(editData.date_of_expiry);
          break;
        case "family":
          if (editData.marital_status !== undefined) updates.marital_status = normalize(editData.marital_status);
          if (editData.fathers_name !== undefined) updates.fathers_name = normalize(editData.fathers_name);
          if (editData.mothers_name !== undefined) updates.mothers_name = normalize(editData.mothers_name);
          break;
        case "location":
          if (editData.province !== undefined) updates.province = normalize(editData.province);
          if (editData.city !== undefined) updates.city = normalize(editData.city);
          if (editData.arrival_date !== undefined) updates.arrival_date = normalize(editData.arrival_date);
          break;
        case "address":
          if (editData.permanent_address !== undefined) updates.permanent_address = normalize(editData.permanent_address);
          break;
      }

      const updated = await updateProfile(updates);
      setProfile(updated);
      setEditingSection(null);
      setEditData({});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update profile");
    } finally {
      setSaving(false);
    }
  }

  function updateField(field: keyof ProfileOut, value: string) {
    setEditData(prev => ({ ...prev, [field]: value || null }));
  }

  const isEditing = (section: SectionKey) => editingSection === section;
  const currentData = editingSection ? editData : profile;

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
            ) : currentData ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ProfileSection 
                  title="Basic information"
                  editing={isEditing("basic")}
                  onEdit={() => startEditing("basic")}
                  onSave={() => saveSection("basic")}
                  onCancel={cancelEditing}
                >
                  <ProfileField 
                    label="Status" 
                    value={currentData.status ?? undefined}
                    editing={isEditing("basic")}
                    onChange={(v) => updateField("status", v)}
                  />
                  <ProfileField 
                    label="Given name" 
                    value={currentData.given_name ?? undefined}
                    editing={isEditing("basic")}
                    onChange={(v) => updateField("given_name", v)}
                  />
                  <ProfileField 
                    label="Surname" 
                    value={currentData.surname ?? undefined}
                    editing={isEditing("basic")}
                    onChange={(v) => updateField("surname", v)}
                  />
                  <ProfileDateField 
                    label="Date of birth" 
                    value={currentData.dob ?? undefined}
                    editing={isEditing("basic")}
                    onChange={(v) => updateField("dob", v)}
                  />
                  <ProfileField 
                    label="Citizenship" 
                    value={currentData.citizenship ?? undefined}
                    editing={isEditing("basic")}
                    onChange={(v) => updateField("citizenship", v)}
                  />
                  <ProfileField 
                    label="Sex" 
                    value={currentData.sex ?? undefined}
                    editing={isEditing("basic")}
                    onChange={(v) => updateField("sex", v)}
                  />
                  <ProfileField 
                    label="Place of birth" 
                    value={currentData.place_of_birth ?? undefined}
                    editing={isEditing("basic")}
                    onChange={(v) => updateField("place_of_birth", v)}
                  />
                </ProfileSection>

                <ProfileSection 
                  title="Passport"
                  editing={isEditing("passport")}
                  onEdit={() => startEditing("passport")}
                  onSave={() => saveSection("passport")}
                  onCancel={cancelEditing}
                >
                  <ProfileField 
                    label="Passport number" 
                    value={currentData.passport_number ?? undefined}
                    editing={isEditing("passport")}
                    onChange={(v) => updateField("passport_number", v)}
                  />
                  <ProfileField 
                    label="Country code" 
                    value={currentData.country_code ?? undefined}
                    editing={isEditing("passport")}
                    onChange={(v) => updateField("country_code", v)}
                  />
                  <ProfileField 
                    label="Personal number" 
                    value={currentData.personal_number ?? undefined}
                    editing={isEditing("passport")}
                    onChange={(v) => updateField("personal_number", v)}
                  />
                  <ProfileDateField 
                    label="Date of issue" 
                    value={currentData.date_of_issue ?? undefined}
                    editing={isEditing("passport")}
                    onChange={(v) => updateField("date_of_issue", v)}
                  />
                  <ProfileDateField 
                    label="Date of expiry" 
                    value={currentData.date_of_expiry ?? undefined}
                    editing={isEditing("passport")}
                    onChange={(v) => updateField("date_of_expiry", v)}
                  />
                </ProfileSection>

                <ProfileSection 
                  title="Family"
                  editing={isEditing("family")}
                  onEdit={() => startEditing("family")}
                  onSave={() => saveSection("family")}
                  onCancel={cancelEditing}
                >
                  <ProfileField 
                    label="Marital status" 
                    value={currentData.marital_status ?? undefined}
                    editing={isEditing("family")}
                    onChange={(v) => updateField("marital_status", v)}
                  />
                  <ProfileField 
                    label="Father's name" 
                    value={currentData.fathers_name ?? undefined}
                    editing={isEditing("family")}
                    onChange={(v) => updateField("fathers_name", v)}
                  />
                  <ProfileField 
                    label="Mother's name" 
                    value={currentData.mothers_name ?? undefined}
                    editing={isEditing("family")}
                    onChange={(v) => updateField("mothers_name", v)}
                  />
                </ProfileSection>

                <ProfileSection 
                  title="Location in Canada"
                  editing={isEditing("location")}
                  onEdit={() => startEditing("location")}
                  onSave={() => saveSection("location")}
                  onCancel={cancelEditing}
                >
                  <ProfileField 
                    label="Province" 
                    value={currentData.province ?? undefined}
                    editing={isEditing("location")}
                    onChange={(v) => updateField("province", v)}
                  />
                  <ProfileField 
                    label="City" 
                    value={currentData.city ?? undefined}
                    editing={isEditing("location")}
                    onChange={(v) => updateField("city", v)}
                  />
                  <ProfileDateField 
                    label="Arrival date" 
                    value={currentData.arrival_date ?? undefined}
                    editing={isEditing("location")}
                    onChange={(v) => updateField("arrival_date", v)}
                  />
                </ProfileSection>

                <div className="lg:col-span-2">
                  <ProfileSection 
                    title="Address"
                    editing={isEditing("address")}
                    onEdit={() => startEditing("address")}
                    onSave={() => saveSection("address")}
                    onCancel={cancelEditing}
                  >
                    <ProfileField 
                      label="Permanent address" 
                      value={currentData.permanent_address ?? undefined}
                      editing={isEditing("address")}
                      onChange={(v) => updateField("permanent_address", v)}
                    />
                  </ProfileSection>
                </div>

                <ProfileSection title="Education">
                  <div className="pt-1">
                    <div className="text-sm font-medium text-slate-600 mb-2">
                      Education (from documents)
                    </div>
                    <EducationSummary data={profile?.education_json} />
                  </div>
                </ProfileSection>

                <ProfileSection title="Language">
                  <div className="pt-1">
                    <div className="text-sm font-medium text-slate-600 mb-2">
                      Language tests (from documents)
                    </div>
                    <LanguageTestsSummary data={profile?.language_json} />
                  </div>
                </ProfileSection>

                <div className="lg:col-span-2">
                  <ProfileSection title="Work experience">
                    <JsonBlock label="Work (from documents)" data={profile?.work_json} />
                  </ProfileSection>
                </div>
              </div>
            ) : null}
            {saving && (
              <div className="fixed bottom-4 right-4 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg">
                Saving...
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
