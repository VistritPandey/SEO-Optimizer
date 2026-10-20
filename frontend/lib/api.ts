import { firebaseAuth } from "@/lib/firebase";
import { requestApi } from "./api-request.mjs";
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const user = firebaseAuth().currentUser;
  if (!user) throw new Error("Sign in to continue.");
  return (await requestApi(path, method, body, (force: boolean) =>
    user.getIdToken(force),
  )) as T;
}
export type Project = {
  id: string;
  spec: {
    name: string;
    website_url: string;
    repository: string;
    enabled: boolean;
    [key: string]: unknown;
  };
  last_report: AuditReport;
  updated_at?: number;
};
export type AuditReport = {
  score?: number | null;
  pages?: number;
  evaluated_checks?: number;
  total_checks?: number;
  model_runtime_ms?: number;
  assessment_reused?: boolean;
  findings?: number;
  tool_trace?: { name: string; success: boolean; runtime_ms?: number }[];
  coverage?: {
    check_id: string;
    title: string;
    module: string;
    state: string;
    reason?: string;
    dependencies?: string[];
    method?: string;
    evidence_ids?: string[];
    evidence_urls?: string[];
    assessment_path?: string;
  }[];
  page_summaries?: {
    url: string;
    title: string;
    excerpt: string;
    evidence_id: string;
  }[];
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
    api_cost_usd?: number | null;
  };
  [key: string]: unknown;
};
export type RecordedEvidence = {
  id: string;
  observation: string;
  url?: string;
  collected_at?: string;
  kind?: string;
  data: unknown;
  [key: string]: unknown;
};
export type Job = {
  id: string;
  status: string;
  kind: string;
  created_at?: number;
  updated_at?: number;
  attempts?: number;
  events: { time: number; message: string }[];
  result: {
    summary?: string;
    verified_fixes?: number;
    pr?: { url: string; number: number };
    verification?: unknown[];
    report?: AuditReport;
    after_report?: AuditReport;
    error_type?: string;
    evidence?: RecordedEvidence[];
    after_evidence?: RecordedEvidence[];
  };
};
export type Activity = {
  jobs: Job[];
  findings: {
    id: string;
    active: boolean;
    details: {
      check_id: string;
      severity: string;
      status: string;
      url?: string;
      evidence_ids?: string[];
      summary?: string;
      evidence_strength?: string;
      dependencies?: string[];
      verification_criteria?: string[];
      action?: { rationale?: string; kind?: string };
      [key: string]: unknown;
    };
  }[];
};
