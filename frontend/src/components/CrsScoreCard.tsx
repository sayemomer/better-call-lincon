import { useMemo } from "react";

type Props = {
  score: number;
  max?: number; // CRS max (default 1200)
  extraNote?: string; // e.g. requirements message when profile is partial
  onRecompute?: () => void;
  recomputing?: boolean;
};

function clamp(n: number, a: number, b: number) {
  return Math.max(a, Math.min(b, n));
}

// Simple “chance” categories for demo UI
function bandLabel(score: number) {
  if (score < 450)
    return {
      label: "Low chance",
      hint: "Likely needs improvement (language, experience, education).",
      pill: "bg-rose-50 text-rose-700 border-rose-200",
    };

  if (score < 600)
    return {
      label: "Medium chance",
      hint: "Competitive in some draws; improvements can help a lot.",
      pill: "bg-amber-50 text-amber-700 border-amber-200",
    };

  return {
    label: "Strong chance",
    hint: "Often competitive, depends on draw type and category.",
    pill: "bg-emerald-50 text-emerald-700 border-emerald-200",
  };
}

export default function CrsScoreCard({ score, max = 1200, extraNote, onRecompute, recomputing }: Props) {
  const s = clamp(score, 0, max);
  const pct = (s / max) * 100;
  const band = useMemo(() => bandLabel(s), [s]);

  // marker position stays inside the bar nicely
  const markerLeft = `calc(${pct}% - 10px)`;

  return (
    <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      {/* soft blobs */}
      <div className="pointer-events-none absolute -right-24 -top-24 h-60 w-60 rounded-full bg-blue-200/50 blur-3xl" />
      <div className="pointer-events-none absolute -left-24 -bottom-24 h-60 w-60 rounded-full bg-emerald-200/40 blur-3xl" />

      <div className="relative flex items-start justify-between gap-3">
        <div>
          <div className="text-xs text-slate-500">CRS score (0–{max})</div>
          <div className="mt-1 text-4xl font-semibold tracking-tight text-slate-900">{s}</div>
          <div className="mt-2 text-sm text-slate-600">{band.hint}</div>
        </div>

        <div className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${band.pill}`}>
          {band.label}
        </div>
      </div>

      {/* segmented bar */}
      <div className="relative mt-6">
        <div className="text-xs text-slate-500">Progress</div>

        <div className="mt-2 h-4 w-full rounded-full border border-slate-200 bg-slate-100 p-1">
          <div
            className="h-full w-full rounded-full"
            style={{
              background:
                "linear-gradient(90deg, #ef4444 0%, #f59e0b 45%, #10b981 75%, #3b82f6 100%)",
            }}
          />
        </div>

        {/* marker */}
        <div className="absolute top-[34px]" style={{ left: markerLeft }}>
          <div className="h-0 w-0 border-x-[10px] border-t-[12px] border-x-transparent border-t-slate-800/80" />
          <div className="mt-1 flex items-center justify-center">
            <div className="rounded-full border border-slate-200 bg-white px-2 py-1 text-[11px] font-semibold text-slate-700 shadow-sm">
              {Math.round(pct)}%
            </div>
          </div>
        </div>

        {/* ticks */}
        <div className="mt-4 flex justify-between text-[11px] text-slate-500">
          <span>0</span>
          <span>450</span>
          <span>600</span>
          <span>{max}</span>
        </div>

        {/* legend */}
        <div className="mt-3 flex flex-wrap gap-3 text-[11px] text-slate-600">
          <span className="inline-flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-rose-500" /> 0–449 Low
          </span>
          <span className="inline-flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500" /> 450–599 Medium
          </span>
          <span className="inline-flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> 600+ Strong
          </span>
        </div>
      </div>

      {extraNote && (
        <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          {extraNote}
        </div>
      )}
      {/* extra credibility copy */}
      <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-3 text-sm text-blue-700">
        We estimate your “chance” based on your CRS range for demo purposes.
        Real Express Entry cutoffs vary by draw type and category.
      </div>
      {onRecompute && (
        <div className="mt-4">
          <button
            type="button"
            onClick={onRecompute}
            disabled={recomputing}
            className="w-full rounded-lg border border-blue-300/60 bg-blue-100/80 px-4 py-2.5 text-sm font-semibold text-blue-800 hover:bg-blue-200/80 disabled:opacity-60 disabled:cursor-not-allowed transition"
          >
            {recomputing ? "Recomputing…" : "Recompute CRS score"}
          </button>
        </div>
      )}
    </div>
  );
}