import {api} from "./api";

export type SignupDocStatus = {
    job_id: string;
    status: string;
    extracted: Record<string, any>;
    reason?: string;
    error?: string;
    needs_email_password: boolean;
    is_error: boolean;
}

export async function uploadSignupDoc(file: File) {
    const form = new FormData();
    form.append("file", file);

    const res = await api.post("/auth/signup-doc", form, {
    headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data as { job_id: string; status: string };
    }

export async function getSignupDocStatus(jobId: string) {
        const res = await api.get(`/auth/signup-doc/${jobId}`);
        return res.data as SignupDocStatus;
    }

export async function finalizeSignup(job_id: string, email: string, password: string) {
        const res = await api.post("/auth/signup-doc/finalize", { job_id, email, password });
        return res.data as { access_token: string; token_type: string; user_id: string; message: string };
}