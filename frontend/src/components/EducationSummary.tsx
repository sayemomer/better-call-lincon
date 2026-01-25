type EduDoc = Record<string, unknown>;

const LEVEL_LABELS: Record<string, string> = {
  secondary: "Secondary school",
  one_two_year_diploma: "One- or two-year diploma/certificate",
  bachelors: "Bachelor's degree",
  masters: "Master's degree",
  phd: "Doctoral (PhD)",
  two_or_more: "Two or more credentials",
};

function levelLabel(v: unknown): string {
  if (v == null || String(v).trim() === "") return "";
  const key = String(v).toLowerCase().replace(/\s+/g, "_");
  return LEVEL_LABELS[key] ?? String(v);
}

function hasAnyEdu(d: EduDoc): boolean {
  return (
    (d.education_level != null && String(d.education_level).trim() !== "") ||
    (d.education_level_detail != null && String(d.education_level_detail).trim() !== "") ||
    d.canadian_education === true ||
    d.canadian_education === false
  );
}

function normalizeEdu(data: unknown): EduDoc | null {
  if (data == null) return null;
  if (typeof data === "object" && !Array.isArray(data) && hasAnyEdu(data as EduDoc)) {
    return data as EduDoc;
  }
  return null;
}

type Props = { data: unknown };

export default function EducationSummary({ data }: Props) {
  const doc = normalizeEdu(data);

  if (!doc) {
    return (
      <div className="rounded-xl border border-slate-200/80 bg-white/60 py-4 px-4 text-sm text-slate-500">
        No education data from documents.
      </div>
    );
  }

  const level = levelLabel(doc.education_level) || (doc.education_level_detail as string) || null;
  const detail = doc.education_level_detail as string | undefined;
  const canadian = doc.canadian_education === true;

  return (
    <div className="rounded-xl border border-emerald-200/60 bg-emerald-50/80 p-4">
      <div className="flex flex-wrap items-center gap-2 text-emerald-800 mb-3">
        {level && <span className="text-sm font-medium">{level}</span>}
        {canadian && (
          <span className="rounded-full bg-emerald-200/80 px-2.5 py-0.5 text-xs font-medium text-emerald-900">
            Canadian education
          </span>
        )}
      </div>
      <div className="space-y-1 text-sm text-slate-700">
        {detail && level !== detail && (
          <div className="text-slate-600">{detail}</div>
        )}
        {!level && !detail && canadian && (
          <div className="text-slate-600">Canadian education</div>
        )}
        {!level && !detail && !canadian && (
          <div className="text-slate-500">No details available.</div>
        )}
      </div>
    </div>
  );
}
