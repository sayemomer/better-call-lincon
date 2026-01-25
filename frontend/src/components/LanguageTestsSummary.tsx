type LangDoc = Record<string, unknown>;

const TEST_LABELS: Record<string, string> = {
  ielts: "IELTS",
  celpip: "CELPIP",
  pte_core: "PTE Core",
  tef_canada: "TEF Canada",
  tcf_canada: "TCF Canada",
};

const SKILLS = ["speaking", "listening", "reading", "writing"] as const;

function formatScore(v: unknown): string {
  if (v == null) return "—";
  const n = typeof v === "number" ? v : parseFloat(String(v));
  return Number.isNaN(n) ? "—" : String(n);
}

function testLabel(d: LangDoc): string {
  const t = (d.test_type ?? d.test ?? d.testType ?? "ielts") as string;
  const key = String(t).toLowerCase().replace(/\s+/g, "_");
  return TEST_LABELS[key] ?? (key ? t : "Language test");
}

function hasAnyScore(d: LangDoc): boolean {
  return SKILLS.some((s) => d[s] != null && String(d[s]).trim() !== "");
}

function normalizeTests(data: unknown): LangDoc[] {
  if (data == null) return [];
  if (Array.isArray(data)) {
    return data.filter((x) => typeof x === "object" && x != null && hasAnyScore(x as LangDoc)) as LangDoc[];
  }
  if (typeof data === "object" && hasAnyScore(data as LangDoc)) {
    return [data as LangDoc];
  }
  return [];
}

type Props = { data: unknown };

export default function LanguageTestsSummary({ data }: Props) {
  const tests = normalizeTests(data);

  if (tests.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200/80 bg-white/60 py-4 px-4 text-sm text-slate-500">
        No language test data from documents.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {tests.map((doc, idx) => (
        <div
          key={idx}
          className="rounded-xl border border-emerald-200/60 bg-emerald-50/80 p-4"
        >
          <div className="flex items-center gap-2 text-emerald-800 mb-3">
            <span className="text-sm font-medium">{testLabel(doc)}</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {SKILLS.map((skill) => (
              <div
                key={skill}
                className="rounded-lg bg-white/80 border border-emerald-100/80 px-3 py-2"
              >
                <div className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                  {skill}
                </div>
                <div className="text-base font-semibold text-slate-900 mt-0.5">
                  {formatScore(doc[skill])}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
