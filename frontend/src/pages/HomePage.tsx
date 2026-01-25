// src/pages/HomePage.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import CrsScoreCard from "../components/CrsScoreCard";
import { signOut } from "../api/authApi";
import { computeCrs, type CRSComputeResponse } from "../api/crs";
import {
  getDocumentsCrsStatus,
  getDocumentsDeadlines,
  uploadDocument,
  type DocumentsCrsStatusResponse,
  type DeadlineItem,
} from "../api/documents";

type DocStatus = {
  id: string;
  name: string;
  required: boolean;
  uploaded: boolean;
  expiresInDays?: number;
};

const REQUIRED_TYPES = new Set([
  "passport", "study_permit", "transcript", "language_test", "education_credential",
  "degree", "diploma", "work_reference", "employment_letter", "ielts", "celpip",
  "pte_core", "tef_canada", "tcf_canada", "proof_funds",
]);

const DISPLAY_NAMES: Record<string, string> = {
  passport: "Passport",
  study_permit: "Study Permit",
  work_permit: "Work Permit",
  transcript: "Transcript",
  proof_funds: "Proof of Funds",
  language_test: "Language Test",
  education_credential: "Education Credential",
  degree: "Degree",
  diploma: "Diploma",
  work_reference: "Work Reference",
  employment_letter: "Employment Letter",
  pay_stubs: "Pay Stubs",
  provincial_nomination: "Provincial Nomination",
  certificate_of_qualification: "Certificate of Qualification",
  enrollment_letter: "Enrollment Letter",
  tax_documents: "Tax Documents",
  ielts: "IELTS",
  celpip: "CELPIP",
  pte_core: "PTE Core",
  tef_canada: "TEF Canada",
  tcf_canada: "TCF Canada",
};

function displayName(type: string): string {
  const k = type.toLowerCase().replace(/\s+/g, "_");
  return DISPLAY_NAMES[k] ?? type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function isRequiredType(type: string): boolean {
  const k = type.toLowerCase().replace(/\s+/g, "_");
  return REQUIRED_TYPES.has(k) || Array.from(REQUIRED_TYPES).some((r) => k.includes(r) || r.includes(k));
}

function daysUntilExpiry(dateStr: string | null | undefined): number | undefined {
  if (!dateStr || typeof dateStr !== "string") return undefined;
  try {
    const [y, m, d] = dateStr.slice(0, 10).split("-").map(Number);
    const expiry = new Date(y, m - 1, d);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    expiry.setHours(0, 0, 0, 0);
    return Math.floor((expiry.getTime() - today.getTime()) / (24 * 60 * 60 * 1000));
  } catch {
    return undefined;
  }
}

function expiryPill(days: number) {
  if (days <= 30) return "text-rose-700 bg-rose-100/60 border-rose-200";
  if (days <= 90) return "text-amber-700 bg-amber-100/60 border-amber-200";
  return "text-emerald-700 bg-emerald-100/60 border-emerald-200";
}

export default function HomePage() {
  const nav = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);
  const [crsData, setCrsData] = useState<CRSComputeResponse | null>(null);
  const [crsLoading, setCrsLoading] = useState(true);
  const [crsError, setCrsError] = useState<string | null>(null);
  const [recomputing, setRecomputing] = useState(false);
  const [docsStatus, setDocsStatus] = useState<DocumentsCrsStatusResponse | null>(null);
  const [deadlines, setDeadlines] = useState<DeadlineItem[]>([]);
  const [docsLoading, setDocsLoading] = useState(true);
  const [docsError, setDocsError] = useState<string | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  function refetchCrs() {
    setCrsError(null);
    computeCrs()
      .then(setCrsData)
      .catch((e) => setCrsError(e instanceof Error ? e.message : "Could not load CRS score."));
  }

  async function handleRecomputeCrs() {
    setRecomputing(true);
    setCrsError(null);
    try {
      const res = await computeCrs();
      setCrsData(res);
    } catch (e) {
      setCrsError(e instanceof Error ? e.message : "Could not load CRS score.");
    } finally {
      setRecomputing(false);
    }
  }

  function refetchDocs() {
    setDocsError(null);
    setDocsLoading(true);
    Promise.all([getDocumentsCrsStatus(), getDocumentsDeadlines()])
      .then(([status, dls]) => {
        setDocsStatus(status);
        setDeadlines(dls);
      })
      .catch((e) => {
        setDocsError(e instanceof Error ? e.message : "Could not load documents.");
      })
      .finally(() => setDocsLoading(false));
  }

  useEffect(() => {
    let ignore = false;
    setCrsLoading(true);
    setCrsError(null);
    computeCrs()
      .then((res) => { if (!ignore) setCrsData(res); })
      .catch((e) => {
        if (!ignore) setCrsError(e instanceof Error ? e.message : "Could not load CRS score.");
      })
      .finally(() => { if (!ignore) setCrsLoading(false); });
    return () => { ignore = true; };
  }, []);

  useEffect(() => {
    let ignore = false;
    setDocsLoading(true);
    setDocsError(null);
    Promise.all([getDocumentsCrsStatus(), getDocumentsDeadlines()])
      .then(([status, dls]) => {
        if (!ignore) {
          setDocsStatus(status);
          setDeadlines(dls);
        }
      })
      .catch((e) => {
        if (!ignore) setDocsError(e instanceof Error ? e.message : "Could not load documents.");
      })
      .finally(() => { if (!ignore) setDocsLoading(false); });
    return () => { ignore = true; };
  }, []);

  function triggerUpload() {
    setUploadError(null);
    fileInputRef.current?.click();
  }

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    const allowed = ["application/pdf", "image/png", "image/jpeg", "image/jpg"];
    if (!allowed.includes(file.type)) {
      setUploadError("Upload a PDF or PNG/JPEG image.");
      return;
    }
    setUploadLoading(true);
    setUploadError(null);
    try {
      await uploadDocument(file);
      refetchDocs();
      refetchCrs();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploadLoading(false);
    }
  }

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await signOut();
      nav("/");
    } finally {
      setLoggingOut(false);
    }
  }

  const docsMap = useMemo(() => {
    const m = new Map<string, { days?: number }>();
    for (const d of deadlines) {
      m.set(d.document_id, { days: d.days_until_expiry ?? undefined });
    }
    return m;
  }, [deadlines]);

  const { docs, requiredCount, uploadedCount, missingRequired } = useMemo(() => {
    const list: DocStatus[] = [];
    let uploadedRequiredCount = 0;
    let missingRequiredCount = 0;

    if (!docsStatus) {
      return { docs: list, requiredCount: 0, uploadedCount: 0, missingRequired: 0 };
    }

    const { uploaded_documents, required_documents } = docsStatus;
    const seen = new Set<string>();
    const uploadedByType = new Map<string, { id: string; days?: number }>();

    for (const u of uploaded_documents) {
      const type = (u.type_detected || "unknown").toLowerCase().replace(/\s+/g, "_");
      let days = docsMap.get(u.id)?.days;
      if (days == null && u.date_of_expiry) {
        days = daysUntilExpiry(u.date_of_expiry);
      }
      const existing = uploadedByType.get(type);
      const useDays = days != null ? days : existing?.days;
      if (!existing || (useDays != null && (existing.days == null || useDays < existing.days))) {
        uploadedByType.set(type, { id: u.id, days: useDays ?? existing?.days });
      }
    }

    for (const [type, { days }] of uploadedByType) {
      const key = `uploaded:${type}`;
      seen.add(key);
      const req = isRequiredType(type);
      if (req) uploadedRequiredCount++;
      list.push({
        id: key,
        name: displayName(type),
        required: req,
        uploaded: true,
        expiresInDays: days != null ? days : undefined,
      });
    }

    for (const r of required_documents) {
      const type = (r.document_type || "unknown").toLowerCase().replace(/\s+/g, "_");
      const key = `missing:${type}`;
      if (seen.has(key)) continue;
      seen.add(key);
      if (r.required_for_crs) missingRequiredCount++;
      list.push({
        id: key,
        name: displayName(type),
        required: r.required_for_crs,
        uploaded: false,
      });
    }

    const requiredTotal = uploadedRequiredCount + missingRequiredCount;
    const uploadedTotal = uploaded_documents.length;
    return {
      docs: list,
      requiredCount: requiredTotal,
      uploadedCount: uploadedTotal,
      missingRequired: missingRequiredCount,
    };
  }, [docsStatus, docsMap]);

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
            <NavItem label="Profile" onClick={() => nav("/profile")} />
            <NavItem label="Chat with immigration AI" onClick={() => nav("/chat")} />
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
              onClick={handleLogout}
              disabled={loggingOut}
              className="px-4 py-2 rounded-lg border border-blue-300/60 text-blue-800 bg-blue-100/60 hover:bg-blue-200/60 text-sm disabled:opacity-60"
            >
              {loggingOut ? "Logging out…" : "Logout"}
            </button>
          </div>

          <main className="p-8 space-y-6">

            {/* TOP ROW */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

              {/* CRS CARD */}
              <div className="rounded-2xl bg-[#e8f1f9] border border-blue-300/30 p-6">
                {crsLoading ? (
                  <CrsScoreCardSkeleton />
                ) : crsError ? (
                  <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                    <div className="text-xs text-slate-500">CRS score (0–1200)</div>
                    <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                      {crsError}
                    </div>
                    <p className="mt-2 text-xs text-slate-500">
                      Upload documents and complete your profile, then retry.
                    </p>
                    <button
                      type="button"
                      onClick={handleRecomputeCrs}
                      disabled={recomputing}
                      className="mt-4 w-full rounded-lg border border-blue-300/60 bg-blue-100/80 px-4 py-2.5 text-sm font-semibold text-blue-800 hover:bg-blue-200/80 disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      {recomputing ? "Recomputing…" : "Recompute CRS score"}
                    </button>
                  </div>
                ) : crsData ? (
                  <CrsScoreCard
                    score={crsData.total}
                    extraNote={
                      (crsData.breakdown?.requirements_status as { message?: string } | undefined)?.message ?? undefined
                    }
                    onRecompute={handleRecomputeCrs}
                    recomputing={recomputing}
                  />
                ) : null}
              </div>

              {/* DOCUMENT SUMMARY */}
              <div className="lg:col-span-2 rounded-2xl bg-[#e8f1f9] border border-blue-300/30 p-6">
                <div className="flex justify-between items-center">
                  <div>
                    <div className="text-lg font-semibold">Document Summary</div>
                    {docsLoading ? (
                      <div className="mt-1 h-5 w-64 animate-pulse rounded bg-slate-200" />
                    ) : docsError ? (
                      <div className="mt-1 text-sm text-rose-700">{docsError}</div>
                    ) : (
                      <div className="text-sm text-slate-600 mt-1">
                        Uploaded {uploadedCount} / {docs.length || 0} • Missing required{" "}
                        <span className="font-semibold text-rose-700">{missingRequired}</span>
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,image/*"
                      className="hidden"
                      onChange={handleFileChange}
                    />
                    <button
                      onClick={triggerUpload}
                      disabled={uploadLoading}
                      className="bg-blue-700 hover:bg-blue-800 text-white px-4 py-2 rounded-lg text-sm font-semibold disabled:opacity-60"
                    >
                      {uploadLoading ? "Uploading…" : "Upload"}
                    </button>
                  </div>
                </div>

                {uploadError && (
                  <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
                    {uploadError}
                  </div>
                )}

                {docsLoading ? (
                  <div className="mt-6 grid grid-cols-3 gap-4">
                    <div className="animate-pulse rounded-xl border border-slate-200 bg-slate-100 p-4" />
                    <div className="animate-pulse rounded-xl border border-slate-200 bg-slate-100 p-4" />
                    <div className="animate-pulse rounded-xl border border-slate-200 bg-slate-100 p-4" />
                  </div>
                ) : docsError ? null : (
                  <div className="grid grid-cols-3 gap-4 mt-6">
                    <MiniStat label="Required docs" value={requiredCount} />
                    <MiniStat label="Uploaded" value={uploadedCount} good />
                    <MiniStat label="Missing" value={missingRequired} bad />
                  </div>
                )}
              </div>
            </div>

            {/* CHECKLIST */}
            <div className="rounded-2xl bg-[#e8f1f9] border border-blue-300/30 p-6">
              <div className="flex justify-between items-center mb-4">
                <div className="text-lg font-semibold">Documents Checklist</div>
                <button
                  onClick={triggerUpload}
                  disabled={uploadLoading}
                  className="px-3 py-2 rounded-lg border border-blue-300/50 bg-blue-100/60 text-blue-800 text-sm disabled:opacity-60"
                >
                  {uploadLoading ? "Uploading…" : "Upload"}
                </button>
              </div>

              {docsLoading ? (
                <div className="space-y-4">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="flex justify-between items-center py-4">
                      <div className="animate-pulse flex-1">
                        <div className="h-4 w-28 rounded bg-slate-200" />
                        <div className="mt-2 h-3 w-16 rounded bg-slate-100" />
                      </div>
                      <div className="h-6 w-20 animate-pulse rounded-full bg-slate-200" />
                    </div>
                  ))}
                </div>
              ) : docsError ? (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                  {docsError}
                </div>
              ) : docs.length === 0 ? (
                <p className="py-6 text-center text-sm text-slate-500">
                  No documents yet. Upload your passport and other documents to get started.
                </p>
              ) : (
                <div className="divide-y divide-blue-300/30">
                  {docs.map((d) => (
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

                        {d.uploaded && (
                          d.expiresInDays != null ? (
                            <span className={`px-3 py-1 rounded-full text-xs border ${expiryPill(d.expiresInDays >= 0 ? d.expiresInDays : 0)}`}>
                              {d.expiresInDays < 0 ? "Expired" : `${d.expiresInDays} days left`}
                            </span>
                          ) : (
                            <span className="px-3 py-1 rounded-full text-xs border border-slate-200 bg-slate-50 text-slate-500">
                              No expiry
                            </span>
                          )
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </main>
        </div>
      </div>
    </div>
  );
}

function CrsScoreCardSkeleton() {
  return (
    <div className="animate-pulse rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="h-4 w-24 rounded bg-slate-200" />
      <div className="mt-3 h-10 w-20 rounded bg-slate-200" />
      <div className="mt-2 h-4 w-full max-w-xs rounded bg-slate-200" />
      <div className="mt-6 h-4 w-16 rounded bg-slate-200" />
      <div className="mt-2 h-4 w-full rounded-full bg-slate-200" />
      <div className="mt-4 flex justify-between">
        <div className="h-3 w-8 rounded bg-slate-200" />
        <div className="h-3 w-12 rounded bg-slate-200" />
        <div className="h-3 w-8 rounded bg-slate-200" />
      </div>
      <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-3">
        <div className="h-4 w-full rounded bg-blue-200/60" />
        <div className="mt-2 h-4 w-3/4 rounded bg-blue-200/40" />
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