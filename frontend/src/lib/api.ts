/**
 * Typed API client — wraps all backend endpoints.
 * Frontend never calls agent service directly.
 */

import axios, { AxiosError } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL!;

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 120_000,   // 2 min for agent responses
  headers: { "Content-Type": "application/json" },
});

// Attach JWT from localStorage
apiClient.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Refresh token on 401
apiClient.interceptors.response.use(
  (res) => res,
  async (err: AxiosError) => {
    const original = err.config as any;
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refresh = localStorage.getItem("refresh_token");
        if (!refresh) throw new Error("No refresh token");
        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refresh,
        });
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        original.headers.Authorization = `Bearer ${data.access_token}`;
        return apiClient(original);
      } catch {
        localStorage.clear();
        window.location.href = "/login";
      }
    }
    return Promise.reject(err);
  }
);


// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const authApi = {
  register: (email: string, name: string, password: string) =>
    apiClient.post("/auth/register", { email, name, password }),

  login: (email: string, password: string) =>
    apiClient.post("/auth/login", { email, password }),

  refresh: (refresh_token: string) =>
    apiClient.post("/auth/refresh", { refresh_token }),

  me: () => apiClient.get("/auth/me"),
};


// ---------------------------------------------------------------------------
// Language
// ---------------------------------------------------------------------------

export const languageApi = {
  translate: (params: {
    input_text: string;
    source_language: string;
    target_language: string;
    context_tone?: string;
    formality_level?: string;
  }) => apiClient.post("/language/translate", params),

  learn: (params: {
    source_language: string;
    target_language: string;
    user_level: string;
    lesson_topic: string;
    session_number?: number;
    previous_topics?: string[];
  }) => apiClient.post("/language/learn", params),

  travelScenario: (params: {
    destination_country: string;
    source_language: string;
    target_language: string;
    scenario_type: string;
  }) => apiClient.post("/language/travel/scenario", params),

  coach: (params: {
    job_field: string;
    coaching_type: string;
    source_language: string;
    target_language: string;
    user_draft?: string;
  }) => apiClient.post("/language/coach", params),

  curriculum: (params: {
    source_language: string;
    target_language: string;
    user_level: string;
    learning_goal: string;
    duration_weeks: number;
  }) => apiClient.post("/language/curriculum", params),

  culture: (params: {
    source_country: string;
    destination_country: string;
    etiquette_context: string;
  }) => apiClient.post("/language/culture", params),

  translationHistory: (limit = 20, offset = 0) =>
    apiClient.get(`/language/history/translations?limit=${limit}&offset=${offset}`),

  progress: () => apiClient.get("/language/profile/progress"),
};


// ---------------------------------------------------------------------------
// Billing
// ---------------------------------------------------------------------------

export const billingApi = {
  plans: () => apiClient.get("/billing/plans"),

  checkout: (plan_name: string, billing_period: "monthly" | "yearly") =>
    apiClient.post("/billing/checkout", { plan_name, billing_period }),

  subscription: () => apiClient.get("/billing/subscription"),
};


// ---------------------------------------------------------------------------
// Admin
// ---------------------------------------------------------------------------

export const adminApi = {
  usageStats: () => apiClient.get("/admin/usage"),
  users: (limit = 50, offset = 0) =>
    apiClient.get(`/admin/users?limit=${limit}&offset=${offset}`),
  health: () => apiClient.get("/admin/health"),
};
