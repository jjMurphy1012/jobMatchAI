const API_BASE = ''

interface ApiResponse<T> {
  data?: T;
  error?: string;
  status?: number;
}

let refreshPromise: Promise<boolean> | null = null

function shouldAttemptRefresh(endpoint: string, retryAuth: boolean) {
  return retryAuth && endpoint !== '/api/auth/refresh' && endpoint !== '/api/auth/logout'
}

async function refreshAuthSession(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    })
      .then((response) => response.ok)
      .catch(() => false)
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

async function request(
  endpoint: string,
  options?: RequestInit,
  retryAuth = true,
): Promise<Response> {
  const headers = new Headers(options?.headers)
  if (!(options?.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    credentials: 'include',
    ...options,
    headers,
  })

  if (response.status === 401 && shouldAttemptRefresh(endpoint, retryAuth)) {
    const refreshed = await refreshAuthSession()
    if (refreshed) {
      return request(endpoint, options, false)
    }
  }

  return response
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
  retryAuth = true,
): Promise<ApiResponse<T>> {
  try {
    const response = await request(endpoint, options, retryAuth)

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }))
      return { error: error.detail || 'Request failed', status: response.status }
    }

    const data = await response.json()
    return { data, status: response.status }
  } catch {
    return { error: 'Network error', status: 0 }
  }
}

export const authApi = {
  googleLoginUrl: () => `${API_BASE}/api/auth/google/login`,
  register: (payload: EmailRegisterPayload) =>
    fetchApi<CurrentUser>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  login: (payload: EmailLoginPayload) =>
    fetchApi<CurrentUser>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  me: () => fetchApi<CurrentUser>('/api/auth/me'),
  logout: () => fetchApi<AuthMessage>('/api/auth/logout', { method: 'POST' }, false),
}

export const adminApi = {
  listUsers: () => fetchApi<AdminUser[]>('/api/admin/users'),
  updateUserRole: (userId: string, role: 'admin' | 'user') =>
    fetchApi<AdminUser>(`/api/admin/users/${userId}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    }),
  listCompanySources: () => fetchApi<CompanySource[]>('/api/admin/company-sources'),
  createCompanySource: (payload: CompanySourcePayload) =>
    fetchApi<CompanySource>('/api/admin/company-sources', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateCompanySource: (id: string, payload: CompanySourcePayload) =>
    fetchApi<CompanySource>(`/api/admin/company-sources/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  deactivateCompanySource: (id: string) =>
    fetchApi<CompanySource>(`/api/admin/company-sources/${id}/deactivate`, {
      method: 'PATCH',
    }),
  syncCompanySource: (id: string) =>
    fetchApi<SourceSyncRun>(`/api/admin/company-sources/${id}/sync`, {
      method: 'POST',
    }),
  listSourceSyncRuns: (limit = 20) =>
    fetchApi<SourceSyncRun[]>(`/api/admin/source-sync-runs?limit=${limit}`),
  listNotifications: (limit = 20) =>
    fetchApi<NotificationLog[]>(`/api/admin/notifications?limit=${limit}`),
  sendTestNotification: (email?: string) =>
    fetchApi<NotificationLog>('/api/admin/notifications/test', {
      method: 'POST',
      body: JSON.stringify({ email: email || undefined }),
    }),
  listInterviewExperiences: (reviewStatus?: InterviewReviewStatus | 'all') => {
    const query = reviewStatus && reviewStatus !== 'all' ? `?review_status=${reviewStatus}` : ''
    return fetchApi<AdminInterviewExperience[]>(`/api/admin/interview-experiences${query}`)
  },
  createInterviewExperience: (payload: AdminInterviewExperiencePayload) =>
    fetchApi<AdminInterviewExperience>('/api/admin/interview-experiences', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  updateInterviewExperience: (id: string, payload: AdminInterviewExperiencePayload) =>
    fetchApi<AdminInterviewExperience>(`/api/admin/interview-experiences/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  updateInterviewExperienceStatus: (id: string, reviewStatus: InterviewReviewStatus) =>
    fetchApi<AdminInterviewExperience>(`/api/admin/interview-experiences/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ review_status: reviewStatus }),
    }),
  importInterviewExperiences: (items: AdminInterviewExperiencePayload[]) =>
    fetchApi<AdminInterviewExperienceImportResponse>('/api/admin/interview-experiences/import', {
      method: 'POST',
      body: JSON.stringify({ items }),
    }),
  deleteInterviewExperience: (id: string) =>
    fetchApi<AuthMessage>(`/api/admin/interview-experiences/${id}`, {
      method: 'DELETE',
    }),
}

export const resumeApi = {
  get: () => fetchApi<ResumeResponse>('/api/resume'),

  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return fetchApi<ResumeResponse>('/api/resume', {
      method: 'POST',
      body: formData,
    })
  },

  delete: () => fetchApi('/api/resume', { method: 'DELETE' }),
}

export const preferencesApi = {
  get: () => fetchApi<PreferenceResponse>('/api/preferences'),

  analyze: (rawText: string) =>
    fetchApi<PreferenceAnalyzeResponse>('/api/preferences/analyze', {
      method: 'POST',
      body: JSON.stringify({ raw_text: rawText }),
    }),

  save: (data: PreferenceData) =>
    fetchApi<PreferenceResponse>('/api/preferences', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  patchFields: (data: PreferencePatchData) =>
    fetchApi<PreferenceResponse>('/api/preferences/fields', {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
}

export const applicationsApi = {
  list: (params: ApplicationListParams = {}) => {
    const query = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== '') query.set(key, String(value))
    })
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return fetchApi<ApplicationListResponse>(`/api/applications${suffix}`)
  },
  create: (payload: ApplicationCreatePayload) =>
    fetchApi<ApplicationRecord>('/api/applications', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  update: (id: string, payload: ApplicationUpdatePayload) =>
    fetchApi<ApplicationRecord>(`/api/applications/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
  remove: (id: string) =>
    fetchApi<null>(`/api/applications/${id}`, {
      method: 'DELETE',
    }),
}

export const jobsApi = {
  list: (skip = 0, limit = 10) =>
    fetchApi<JobListResponse>(`/api/jobs?skip=${skip}&limit=${limit}`),

  get: (id: string) => fetchApi<JobResponse>(`/api/jobs/${id}`),

  refresh: () => fetchApi<JobRefreshResponse>('/api/jobs/refresh', { method: 'POST' }),

  generateCoverLetter: (id: string) =>
    fetchApi<CoverLetterResponse>(`/api/jobs/${id}/cover-letter`, { method: 'POST' }),

  markApplied: (id: string) =>
    fetchApi(`/api/jobs/${id}/apply`, { method: 'PUT' }),
}

export const tasksApi = {
  list: () => fetchApi<DailyTasksResponse>('/api/daily-tasks'),

  complete: (id: string) =>
    fetchApi<TaskCompleteResponse>(`/api/daily-tasks/${id}/complete`, { method: 'PUT' }),

  uncomplete: (id: string) =>
    fetchApi(`/api/daily-tasks/${id}/uncomplete`, { method: 'PUT' }),

  stats: () => fetchApi<TaskStatsResponse>('/api/daily-tasks/stats'),
}

export const interviewExperiencesApi = {
  list: (filters: InterviewExperienceFilters = {}) => {
    const params = new URLSearchParams()
    params.set('limit', String(filters.limit ?? 12))
    if (filters.company) params.set('company', filters.company)
    if (filters.role) params.set('role', filters.role)
    if (filters.level) params.set('level', filters.level)
    if (filters.topic) params.set('topic', filters.topic)
    if (filters.year) params.set('year', String(filters.year))
    return fetchApi<InterviewExperience[]>(`/api/interview-experiences?${params.toString()}`)
  },
}

export interface AuthMessage {
  message: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  role: 'admin' | 'user';
  is_disabled: boolean;
}

export interface EmailRegisterPayload {
  name?: string;
  email: string;
  password: string;
}

export interface EmailLoginPayload {
  email: string;
  password: string;
}

export interface AdminUser extends CurrentUser {
  created_at?: string;
  last_login_at?: string;
}

export interface CompanySource {
  id: string;
  source_type: 'greenhouse';
  company_name: string;
  board_token: string;
  is_active: boolean;
  last_synced_at?: string;
  created_by_user_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CompanySourcePayload {
  source_type: 'greenhouse';
  company_name: string;
  board_token: string;
  is_active: boolean;
}

export interface SourceSyncRun {
  id: string;
  company_source_id: string;
  source_type: 'greenhouse';
  status: 'running' | 'success' | 'failed';
  started_at?: string;
  finished_at?: string;
  fetched_count: number;
  upserted_count: number;
  closed_count: number;
  error_message?: string;
  company_name?: string;
  board_token?: string;
}

export type ApplicationStatus =
  | 'saved'
  | 'applying'
  | 'applied'
  | 'assessment'
  | 'interviewing'
  | 'offer'
  | 'rejected'
  | 'withdrawn';

export type ApplicationChannel = 'online' | 'referral';
export type ApplicationJobType = 'full_time' | 'internship' | 'new_grad' | 'contract';

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  saved: 'Saved',
  applying: 'Applying',
  applied: 'Applied',
  assessment: 'OA / Assessment',
  interviewing: 'Interviewing',
  offer: 'Offer',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
};

export const APPLICATION_JOB_TYPE_LABELS: Record<ApplicationJobType, string> = {
  full_time: 'Full Time',
  internship: 'Internship',
  new_grad: 'New Grad',
  contract: 'Contract',
};

export interface ApplicationRecord {
  id: string;
  company_name: string;
  job_title: string;
  location?: string;
  job_url?: string;
  job_type?: ApplicationJobType;
  season?: string;
  channel: ApplicationChannel;
  status: ApplicationStatus;
  applied_at?: string;
  notes?: string;
  opportunity_id?: string;
  user_job_match_id?: string;
  status_updated_at?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ApplicationListResponse {
  applications: ApplicationRecord[];
  status_counts: Partial<Record<ApplicationStatus, number>>;
  total: number;
}

export interface ApplicationListParams {
  status?: ApplicationStatus;
  job_type?: ApplicationJobType;
  channel?: ApplicationChannel;
  search?: string;
  limit?: number;
  offset?: number;
}

export interface ApplicationCreatePayload {
  user_job_match_id?: string;
  company_name?: string;
  job_title?: string;
  location?: string;
  job_url?: string;
  job_type?: ApplicationJobType;
  season?: string;
  channel: ApplicationChannel;
  status: ApplicationStatus;
  applied_at?: string;
  notes?: string;
}

export type ApplicationUpdatePayload = Partial<Omit<ApplicationCreatePayload, 'user_job_match_id'>>;

export interface NotificationLog {
  id: string;
  user_id: string;
  kind: 'daily_digest' | 'test';
  provider: string;
  recipient: string;
  subject?: string;
  status: 'sent' | 'failed' | 'skipped';
  attempts: number;
  provider_message_id?: string;
  error_message?: string;
  match_count: number;
  sent_for_date?: string;
  created_at?: string;
}

export interface AdminInterviewExperience {
  id: string;
  company_name: string;
  company_name_normalized: string;
  role: string;
  level?: string;
  year?: number;
  rounds?: string;
  topics: string[];
  summary: string;
  source_url?: string;
  source_site?: string;
  review_status: InterviewReviewStatus;
  relevance_keywords: string[];
  created_by_user_id?: string;
  reviewed_by_user_id?: string;
  reviewed_at?: string;
  created_at?: string;
  updated_at?: string;
}

export interface AdminInterviewExperiencePayload {
  company_name: string;
  role: string;
  level?: string | null;
  year?: number | null;
  rounds?: string | null;
  topics: string[];
  summary: string;
  source_url?: string | null;
  source_site?: string | null;
  review_status: InterviewReviewStatus;
  relevance_keywords: string[];
}

export interface AdminInterviewExperienceImportResponse {
  imported_count: number;
  experiences: AdminInterviewExperience[];
}

export type InterviewReviewStatus = 'draft' | 'needs_review' | 'published' | 'rejected';

export interface ResumeResponse {
  id: string;
  file_name: string;
  uploaded_at: string;
  content_preview?: string;
  storage_provider?: string;
  download_url?: string;
}

export interface PreferenceResponse {
  id: string;
  raw_text?: string;
  extracted_fields: PreferenceFields;
  override_fields: PreferenceOverrideFields;
  effective_fields: PreferenceFields;
  extracted_at?: string;
  extraction_version?: string;
  reminder_enabled: boolean;
  reminder_email?: string;
}

export interface PreferenceAnalyzeResponse {
  raw_text: string;
  extracted_fields: PreferenceFields;
  effective_fields: PreferenceFields;
  extracted_at: string;
  extraction_version: string;
  used_fallback: boolean;
}

export interface PreferenceFields {
  keywords: string[];
  locations: string[];
  is_intern: boolean;
  need_sponsor: boolean;
  experience_level?: 'entry' | 'mid' | 'senior';
  remote_preference?: 'remote' | 'hybrid' | 'onsite';
  excluded_companies: string[];
  industries: string[];
  salary_min?: number;
  salary_max?: number;
  salary_currency?: string;
}

export interface PreferenceData {
  raw_text: string;
  extracted_fields?: PreferenceFields;
  override_fields?: PreferenceOverrideFields;
  reminder_enabled: boolean;
  reminder_email?: string;
}

export interface PreferencePatchData {
  override_fields?: PreferenceOverrideFields;
  reminder_enabled?: boolean;
  reminder_email?: string;
}

export interface PreferenceOverrideFields {
  keywords?: string[];
  locations?: string[];
  is_intern?: boolean;
  need_sponsor?: boolean;
  experience_level?: 'entry' | 'mid' | 'senior' | null;
  remote_preference?: 'remote' | 'hybrid' | 'onsite' | null;
  excluded_companies?: string[];
  industries?: string[];
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
}

export interface JobResponse {
  id: string;
  source_type?: string;
  source_job_id?: string;
  title: string;
  company: string;
  location?: string;
  salary?: string;
  url?: string;
  match_score: number;
  match_reason?: string;
  matched_skills?: string;
  missing_skills?: string;
  cover_letter?: string;
  is_applied: boolean;
  searched_at: string;
  application_status?: string;
  related_interviews: JobRelatedInterviewExperience[];
}

export interface JobRelatedInterviewExperience {
  id: string;
  company_name: string;
  role: string;
  level?: string;
  year?: number;
  topics: string[];
  summary: string;
  source_url?: string;
  source_site?: string;
  relevance_score: number;
}

export interface JobListResponse {
  jobs: JobResponse[];
  total: number;
  last_search?: string;
}

export interface JobRefreshResponse {
  message: string;
  status: 'completed';
  jobs_found: number;
  final_threshold?: number;
  used_synced_opportunities: boolean;
  source_counts: Record<string, number>;
  candidate_stats: Record<string, number | string | boolean>;
}

export interface CoverLetterResponse {
  job_id: string;
  cover_letter: string;
}

export interface DailyTask {
  id: string;
  job: {
    id: string;
    title: string;
    company: string;
    location?: string;
    url?: string;
    match_score: number;
  };
  is_completed: boolean;
  completed_at?: string;
  task_order: number;
}

export interface DailyTasksResponse {
  tasks: DailyTask[];
  total: number;
  completed: number;
  date: string;
  all_completed: boolean;
}

export interface TaskCompleteResponse {
  message: string;
  task_id: string;
  all_completed: boolean;
  celebration_message?: string;
}

export interface TaskStatsResponse {
  today_total: number;
  today_completed: number;
  today_remaining: number;
  completion_rate: number;
  all_completed: boolean;
  streak_days: number;
}

export interface InterviewExperience {
  id: string;
  company_name: string;
  role: string;
  level?: string;
  year?: number;
  rounds?: string;
  topics: string[];
  summary: string;
  source_url?: string;
  source_site?: string;
  relevance_score: number;
  matched_company: boolean;
}

export interface InterviewExperienceFilters {
  limit?: number;
  company?: string;
  role?: string;
  level?: string;
  topic?: string;
  year?: number;
}
