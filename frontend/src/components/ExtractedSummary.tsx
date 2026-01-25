type Extracted = Record<string, unknown>;

function formatDate(s: unknown): string | null {
  if (typeof s !== "string" || !s) return null;
  try {
    const [y, m, d] = s.split("-").map(Number);
    if (!y || !m || !d) return null;
    const date = new Date(y, m - 1, d);
    if (Number.isNaN(date.getTime())) return null;
    return date.toLocaleDateString("en-CA", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return null;
  }
}

type Props = { extracted: Extracted };

export default function ExtractedSummary({ extracted }: Props) {
  const e = extracted ?? {};
  const name = (e.name as string) || [e.given_name, e.surname].filter(Boolean).join(" ") || null;
  const dob = formatDate(e.dob);
  const citizenship = (e.citizenship as string) || null;
  const sex = (e.sex as string) || null;
  const expiry = formatDate(e.date_of_expiry);
  const passportNumber = (e.passport_number as string) || null;

  if (!name && !dob && !citizenship) return null;

  return (
    <div className="rounded-2xl border border-emerald-200/60 bg-emerald-50/80 p-4">
      <div className="flex items-center gap-2 text-emerald-800">
        <span className="text-base" aria-hidden>
          ✓
        </span>
        <span className="text-sm font-medium">Passport validated</span>
      </div>
      <div className="mt-3 space-y-1.5 text-sm text-slate-700">
        {name && (
          <div className="font-medium text-slate-900">
            {name}
          </div>
        )}
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-slate-600">
          {dob && <span>Born {dob}</span>}
          {citizenship && <span>{citizenship}</span>}
          {sex && <span>{sex}</span>}
        </div>
        {expiry && (
          <div className="text-xs text-slate-500">
            Passport expires {expiry}
          </div>
        )}
        {passportNumber && passportNumber.length >= 8 && (
          <div className="text-xs text-slate-500 font-mono tracking-tight">
            {passportNumber.slice(0, 4)}••••{passportNumber.slice(-4)}
          </div>
        )}
      </div>
    </div>
  );
}
