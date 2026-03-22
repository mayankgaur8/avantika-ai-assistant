/**
 * Zustand global store — auth, user preferences, UI state.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, accessToken: string, refreshToken: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      setAuth: (user, accessToken, refreshToken) => {
        localStorage.setItem("access_token", accessToken);
        localStorage.setItem("refresh_token", refreshToken);
        set({ user, accessToken, refreshToken, isAuthenticated: true });
      },

      clearAuth: () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        set({ user: null, accessToken: null, refreshToken: null, isAuthenticated: false });
      },
    }),
    { name: "avantika-auth" }
  )
);


interface PreferencesState {
  sourceLanguage: string;
  targetLanguage: string;
  userLevel: string;
  setSourceLanguage: (v: string) => void;
  setTargetLanguage: (v: string) => void;
  setUserLevel: (v: string) => void;
}

export const usePreferences = create<PreferencesState>()(
  persist(
    (set) => ({
      sourceLanguage: "Hindi",
      targetLanguage: "English",
      userLevel: "beginner",
      setSourceLanguage: (v) => set({ sourceLanguage: v }),
      setTargetLanguage: (v) => set({ targetLanguage: v }),
      setUserLevel: (v) => set({ userLevel: v }),
    }),
    { name: "avantika-prefs" }
  )
);
