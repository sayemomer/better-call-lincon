// src/pages/HomePage.tsx
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import CrsScoreCard from "../components/CrsScoreCard";


type DocStatus = {
  id: string;
  name: string;
  required: boolean;
  uploaded: boolean;
  expiresInDays?: number;
};

function expiryPill(days: number) {
  if (days <= 30) return "text-rose-700 bg-rose-100/60 border-rose-200";
  if (days <= 90) return "text-amber-700 bg-amber-100/60 border-amber-200";
  return "text-emerald-700 bg-emerald-100/60 border-emerald-200";
}

export default function HomePage() {
  const nav = useNavigate();
  const crsScore = 645;

  const docs: DocStatus[] = useMemo(
    () => [
      { id: "passport", name: "Passport", required: true, uploaded: true, expiresInDays: 420 },
      { id: "study_permit", name: "Study Permit", required: true, uploaded: true, expiresInDays: 90 },
      { id: "transcript", name: "Transcript", required: true, uploaded: false },
      { id: "proof_funds", name: "Proof of Funds", required: true, uploaded: false },
      { id: "work_permit", name: "Work Permit", required: false, uploaded: false },
    ],
    []
  );

  const requiredCount = docs.filter(d => d.required).length;
  const uploadedCount = docs.filter(d => d.uploaded).length;
  const missingRequired = docs.filter(d => d.required && !d.uploaded).length;

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
            <NavItem active label="Home" onClick={() => nav("/home")} />
            <NavItem label="Upload Documents" onClick={() => nav("/documents")} />
            <NavItem label="Deadlines" onClick={() => nav("/deadlines")} />
            <NavItem label="Eligibility" onClick={() => nav("/eligibility")} />
            <NavItem label="Policy Updates" onClick={() => nav("/updates")} />
            <NavItem label="chat with AI" onClick={() => nav("/chat")} />
            <NavItem label="About Us" onClick={() => nav("/about")} />
          </div>
        </aside>

        {/* MAIN */}
        <div className="flex-1">

          {/* TOP BAR */}
          <div className="bg-[#dde9f5] border-b border-blue-300/40 px-8 py-4 flex justify-between items-center">
            <div>
              <div className="text-xs text-slate-500">Dashboard</div>
              <div className="text-xl font-semibold text-slate-900">Overview</div>
            </div>

            <button
              onClick={() => nav("/")}
              className="px-4 py-2 rounded-lg border border-blue-300/60 text-blue-800 bg-blue-100/60 hover:bg-blue-200/60 text-sm"
            >
              Logout
            </button>
          </div>

          <main className="p-8 space-y-6">

            {/* TOP ROW */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

              {/* CRS CARD */}
              <div className="rounded-2xl bg-[#e8f1f9] border border-blue-300/30 p-6">
                <CrsScoreCard score={crsScore} />
              </div>

              {/* DOCUMENT SUMMARY */}
              <div className="lg:col-span-2 rounded-2xl bg-[#e8f1f9] border border-blue-300/30 p-6">
                <div className="flex justify-between items-center">
                  <div>
                    <div className="text-lg font-semibold">Document Summary</div>
                    <div className="text-sm text-slate-600 mt-1">
                      Uploaded {uploadedCount} / {docs.length} • Missing required{" "}
                      <span className="font-semibold text-rose-700">{missingRequired}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => nav("/documents")}
                    className="bg-blue-700 hover:bg-blue-800 text-white px-4 py-2 rounded-lg text-sm font-semibold"
                  >
                    Upload
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-4 mt-6">
                  <MiniStat label="Required docs" value={requiredCount} />
                  <MiniStat label="Uploaded" value={uploadedCount} good />
                  <MiniStat label="Missing" value={missingRequired} bad />
                </div>
              </div>
            </div>

            {/* CHECKLIST */}
            <div className="rounded-2xl bg-[#e8f1f9] border border-blue-300/30 p-6">
              <div className="flex justify-between items-center mb-4">
                <div className="text-lg font-semibold">Documents Checklist</div>
                <button
                  onClick={() => nav("/documents")}
                  className="px-3 py-2 rounded-lg border border-blue-300/50 bg-blue-100/60 text-blue-800 text-sm"
                >
                  Go to uploads
                </button>
              </div>

              <div className="divide-y divide-blue-300/30">
                {docs.map(d => (
                  <div
                    key={d.id}
                    className={`flex justify-between items-center py-4 ${
                      !d.uploaded && d.required ? "bg-rose-100/40 px-4 rounded-lg" : ""
                    }`}
                  >
                    <div>
                      <div className="font-medium">{d.name}</div>
                      <div className="text-xs text-slate-500">
                        {d.required ? "Required" : "Optional"}
                      </div>
                    </div>

                    <div className="flex gap-3 items-center">
                      {d.uploaded ? (
                        <span className="px-3 py-1 rounded-full text-xs bg-emerald-100/60 text-emerald-800 border border-emerald-200">
                          Uploaded
                        </span>
                      ) : (
                        <span className="px-3 py-1 rounded-full text-xs bg-rose-100/60 text-rose-800 border border-rose-200">
                          Missing
                        </span>
                      )}

                      {d.uploaded && d.expiresInDays && (
                        <span className={`px-3 py-1 rounded-full text-xs border ${expiryPill(d.expiresInDays)}`}>
                          {d.expiresInDays} days left
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </main>
        </div>
      </div>
    </div>
  );
}

/* NAV ITEM */
function NavItem({ label, onClick, active }: { label: string; onClick: () => void; active?: boolean }) {
  return (
    <button
      onClick={onClick}
      className={`w-full px-4 py-2 rounded-lg text-sm font-medium text-left transition ${
        active
          ? "bg-blue-700 text-white shadow-sm"
          : "text-slate-700 hover:bg-blue-200/60"
      }`}
    >
      {label}
    </button>
  );
}

/* MINI STAT */
function MiniStat({
  label,
  value,
  good,
  bad,
}: {
  label: string;
  value: number;
  good?: boolean;
  bad?: boolean;
}) {
  let style = "bg-blue-100/60 text-blue-800 border-blue-200";

  if (good) style = "bg-emerald-100/60 text-emerald-800 border-emerald-200";
  if (bad) style = "bg-rose-100/60 text-rose-800 border-rose-200";

  return (
    <div className={`rounded-xl border p-4 ${style}`}>
      <div className="text-xs">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
    </div>
  );
}