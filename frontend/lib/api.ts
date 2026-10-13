import { firebaseAuth } from "./firebase";
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const user = firebaseAuth().currentUser;
  if (!user) throw new Error("Sign in to continue.");
  const token = await user.getIdToken();
  const response = await fetch("/api/backend/" + path, {
    method,
    headers: {
      Authorization: "Bearer " + token,
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
  const result = await response.json();
  if (!response.ok)
    throw new Error(
      typeof result.detail === "string"
        ? result.detail
        : "Request failed. Please check your inputs.",
    );
  return result as T;
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
  last_report: {
    score?: number;
    pages?: number;
    verified_fixes?: number;
    findings?: number;
    [key: string]: unknown;
  };
};
export type RecordedEvidence = {
  id: string;
  observation: string;
  data: unknown;
  [key: string]: unknown;
};
export type Job = {
  id: string;
  status: string;
  kind: string;
  events: { time: number; message: string }[];
  result: {
    summary?: string;
    verified_fixes?: number;
    pr?: { url: string; number: number };
    verification?: unknown[];
    report?: unknown;
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
      [key: string]: unknown;
    };
  }[];
};
