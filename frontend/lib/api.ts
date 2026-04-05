const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type JobStatus =
  | "suggested"
  | "active"
  | "processing"
  | "rejected"
  | "dismissed"
  | "failed"
  ;

export type StageName = "applied" | "oa" | "interview" | "offer";

export interface JobStageResponse {
  stage_name: StageName;
  completed_at?: string | null;
  notes?: string | null;
}

export interface Job {
  id: number;
  url: string;
  company: string;
  title: string;
  status: JobStatus;
  score?: number | null;
  requirements?: string[] | null;
  error_message?: string | null;
  stages?: JobStageResponse[];
  rejection_stage?: StageName | null;
  rejection_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface StageUpdate {
  name: StageName;
  completed: boolean;
  notes?: string | null;
}

export interface UpdateJobStagesPayload {
  stages: StageUpdate[];
  rejection_stage?: StageName | null;
  rejection_reason?: string | null;
}

export interface JobWithStagesResponse {
  id: number;
  url: string;
  company: string;
  title: string;
  status: JobStatus;
  score?: number | null;
  stages: JobStageResponse[];
  rejection_stage?: StageName | null;
  rejection_reason?: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobSource {
  id: number;
  url: string;
  name: string;
  filter_prompt?: string | null;
  last_scraped_at?: string | null;
  created_at: string;
}

export interface JobInfo {
  id?: number | null;
  title: string;
  company: string;
  url: string;
  score?: number | null;
  skip_reason?: string | null;
}

export interface SourceScanResult {
  source_id: number;
  source_name: string;
  source_url: string;
  jobs_found: number;
  jobs_added: number;
  jobs_skipped: number;
  added_jobs: JobInfo[];
  skipped_jobs: JobInfo[];
  error?: string | null;
}

export interface ScanStatus {
  is_scanning: boolean;
  current_source?: string | null;
  current_source_id?: number | null;
  sources_total: number;
  sources_completed: number;
  jobs_found: number;
  jobs_scored: number;
  current_step?: string | null;
  error?: string | null;
  source_results: SourceScanResult[];
  active_sources: string[];
}

interface RefreshResponse {
  message: string;
  sources_count: number;
}

interface RequestOptions extends RequestInit {
  skipJson?: boolean;
}

async function request<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const { skipJson, ...fetchOptions } = options;
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(fetchOptions.headers ?? {}),
    },
    ...fetchOptions,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const err = await response.json();
      detail = err.detail ?? err.message ?? detail;
    } catch {
      // Ignore JSON parse errors and use HTTP status text.
    }
    throw new Error(detail);
  }

  if (skipJson) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function applyForJob(url: string): Promise<Job> {
  return request<Job>("/apply", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function getJobs(): Promise<Job[]> {
  return request<Job[]>("/jobs");
}

export async function getJob(id: number): Promise<Job> {
  return request<Job>(`/jobs/${id}`);
}

export function getResumePdfUrl(jobId: number): string {
  return `${API_BASE}/jobs/${jobId}/pdf`;
}

export async function getGlobalFilter(): Promise<string> {
  const response = await request<{ filter_prompt: string }>(
    "/settings/global-filter",
  );
  return response.filter_prompt;
}

export async function updateGlobalFilter(
  filter_prompt: string,
): Promise<string> {
  const response = await request<{ filter_prompt: string }>(
    "/settings/global-filter",
    {
      method: "PUT",
      body: JSON.stringify({ filter_prompt }),
    },
  );
  return response.filter_prompt;
}

export async function getSources(): Promise<JobSource[]> {
  return request<JobSource[]>("/sources");
}

export async function createSource(
  name: string,
  url: string,
  filter_prompt?: string,
): Promise<JobSource> {
  return request<JobSource>("/sources", {
    method: "POST",
    body: JSON.stringify({ name, url, filter_prompt }),
  });
}

export async function updateSource(
  sourceId: number,
  updates: Partial<Pick<JobSource, "name" | "url" | "filter_prompt">>,
): Promise<JobSource> {
  return request<JobSource>(`/sources/${sourceId}`, {
    method: "PUT",
    body: JSON.stringify(updates),
  });
}

export async function deleteSource(sourceId: number): Promise<void> {
  await request<void>(`/sources/${sourceId}`, {
    method: "DELETE",
    skipJson: true,
  });
}

export async function getSuggestions(): Promise<Job[]> {
  return request<Job[]>("/suggestions");
}

export async function refreshSuggestions(
  source_ids?: number[],
): Promise<RefreshResponse> {
  const payload =
    source_ids && source_ids.length > 0 ? { source_ids } : undefined;
  return request<RefreshResponse>("/suggestions/refresh", {
    method: "POST",
    body: payload ? JSON.stringify(payload) : undefined,
  });
}

export async function dismissJob(jobId: number): Promise<Job> {
  return request<Job>(`/jobs/${jobId}/dismiss`, {
    method: "POST",
  });
}

export async function updateJobStages(
  jobId: number,
  payload: UpdateJobStagesPayload,
): Promise<JobWithStagesResponse> {
  return request<JobWithStagesResponse>(`/jobs/${jobId}/stages`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function getScanStatus(): Promise<ScanStatus> {
  return request<ScanStatus>("/suggestions/status");
}
