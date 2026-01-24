import { useEffect, useMemo, useState } from "react";
import { uploadSignupDoc, getSignupDocStatus, finalizeSignup } from "@/lib/authapi";
import type { SignupDocStatus } from "@/lib/authapi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Props = {
  onAuthed: (accessToken: string) => void;
};

export default function SignupDocPage({ onAuthed }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<SignupDocStatus | null>(null);
  const [loadingUpload, setLoadingUpload] = useState(false);
  const [loadingFinalize, setLoadingFinalize] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // finalize form
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const canFinalize = useMemo(() => {
    return !!status?.needs_email_password && !status?.is_error && status?.status !== "failed";
  }, [status]);

  async function onUpload() {
    if (!file) return;
    setApiError(null);
    setLoadingUpload(true);
    try {
      const res = await uploadSignupDoc(file);
      setJobId(res.job_id);
      setStatus(null);
    } catch (e: any) {
      setApiError(e?.response?.data?.detail ?? "Upload failed");
    } finally {
      setLoadingUpload(false);
    }
  }

  // Poll job status
  useEffect(() => {
    if (!jobId) return;

    let stopped = false;
    const tick = async () => {
      try {
        const s = await getSignupDocStatus(jobId);
        if (!stopped) setStatus(s);

        // stop polling if terminal
        const terminal = ["completed", "failed", "invalid_document", "need_review", "needs_review"].includes(s.status);
        if (!terminal && !stopped) {
          setTimeout(tick, 2000);
        }
      } catch (e: any) {
        if (!stopped) setApiError(e?.response?.data?.detail ?? "Failed to fetch status");
      }
    };

    tick();
    return () => {
      stopped = true;
    };
  }, [jobId]);

  async function onFinalize() {
    if (!jobId) return;
    setApiError(null);
    setLoadingFinalize(true);
    try {
      const res = await finalizeSignup(jobId, email, password);
      onAuthed(res.access_token);
    } catch (e: any) {
      setApiError(e?.response?.data?.detail ?? "Finalize failed");
    } finally {
      setLoadingFinalize(false);
    }
  }

  return (
    <Card className="rounded-2xl shadow-sm">
      <CardHeader>
        <CardTitle>Signup via Document</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Upload */}
        <div className="space-y-2">
          <Label>Upload PDF / JPG / PNG</Label>
          <Input
            type="file"
            accept="application/pdf,image/png,image/jpeg"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          <Button disabled={!file || loadingUpload} onClick={onUpload}>
            {loadingUpload ? "Uploading..." : "Upload & Extract"}
          </Button>
        </div>

        {/* Status */}
        {jobId && (
          <div className="space-y-2">
            <div className="text-sm text-muted-foreground">Job: {jobId}</div>
            <div className="text-sm">
              Status: <span className="font-medium">{status?.status ?? "loading..."}</span>
            </div>

            {!!status?.reason && (
              <div className="text-sm text-muted-foreground">Reason: {status.reason}</div>
            )}

            {!!status?.error && (
              <div className="text-sm text-red-600">Error: {status.error}</div>
            )}

            {status?.extracted && (
              <pre className="text-xs bg-muted p-3 rounded-xl overflow-auto">
{JSON.stringify(status.extracted, null, 2)}
              </pre>
            )}
          </div>
        )}

        {/* Finalize */}
        {canFinalize && (
          <div className="space-y-3 border-t pt-4">
            <div className="text-sm font-medium">Finalize account</div>

            <div className="space-y-2">
              <Label>Email</Label>
              <Input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
            </div>

            <div className="space-y-2">
              <Label>Password</Label>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Min 8 characters"
              />
            </div>

            <Button disabled={loadingFinalize || !email || password.length < 8} onClick={onFinalize}>
              {loadingFinalize ? "Creating account..." : "Create account"}
            </Button>
          </div>
        )}

        {apiError && <div className="text-sm text-red-600">{apiError}</div>}
      </CardContent>
    </Card>
  );
}