const API_BASE = import.meta.env.VITE_API_URL || '';

interface ApiResponse<T> {
  data?: T;
  error?: string;
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      return { error: error.detail || 'Request failed' };
    }

    const data = await response.json();
    return { data };
  } catch (err) {
    return { error: 'Network error' };
  }
}

// Resume API
export const resumeApi = {
  get: () => fetchApi<ResumeResponse>('/api/resume'),

  upload: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE}/api/resume`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
        return { error: error.detail };
      }

      const data = await response.json();
      return { data };
    } catch {
      return { error: 'Network error' };
    }
  },

  delete: () => fetchApi('/api/resume', { method: 'DELETE' }),
};

// Preferences API
export const preferencesApi = {
  get: () => fetchApi<PreferenceResponse>('/api/preferences'),

  save: (data: PreferenceData) =>
    fetchApi<PreferenceResponse>('/api/preferences', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

// Jobs API
export const jobsApi = {
  list: (skip = 0, limit = 10) =>
    fetchApi<JobListResponse>(`/api/jobs?skip=${skip}&limit=${limit}`),

  get: (id: string) => fetchApi<JobResponse>(`/api/jobs/${id}`),

  refresh: () => fetchApi('/api/jobs/refresh', { method: 'POST' }),

  markApplied: (id: string) =>
    fetchApi(`/api/jobs/${id}/apply`, { method: 'PUT' }),
};

// Daily Tasks API
export const tasksApi = {
  list: () => fetchApi<DailyTasksResponse>('/api/daily-tasks'),

  complete: (id: string) =>
    fetchApi<TaskCompleteResponse>(`/api/daily-tasks/${id}/complete`, { method: 'PUT' }),

  uncomplete: (id: string) =>
    fetchApi(`/api/daily-tasks/${id}/uncomplete`, { method: 'PUT' }),

  stats: () => fetchApi<TaskStatsResponse>('/api/daily-tasks/stats'),
};

// Types
export interface ResumeResponse {
  id: string;
  file_name: string;
  uploaded_at: string;
  content_preview?: string;
}

export interface PreferenceResponse {
  id: string;
  keywords: string;
  location?: string;
  is_intern: boolean;
  need_sponsor: boolean;
  experience_level?: string;
  job_description?: string;
  remote_preference?: string;
  reminder_enabled: boolean;
  reminder_email?: string;
}

export interface PreferenceData {
  keywords: string;
  location?: string;
  is_intern: boolean;
  need_sponsor: boolean;
  experience_level?: string;
  job_description?: string;
  remote_preference?: string;
  reminder_enabled: boolean;
  reminder_email?: string;
}

export interface JobResponse {
  id: string;
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
}

export interface JobListResponse {
  jobs: JobResponse[];
  total: number;
  last_search?: string;
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
