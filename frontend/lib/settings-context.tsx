"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  DEFAULT_SETTINGS,
  getSettings,
  setSettings as persistSettings,
  type Settings,
} from "@/lib/settings";

type SettingsContextValue = {
  settings: Settings;
  updateSettings: (partial: Partial<Settings>) => void;
  reloadSettings: () => void;
};

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettingsState] = useState<Settings>(DEFAULT_SETTINGS);

  useEffect(() => {
    setSettingsState(getSettings());
  }, []);

  const updateSettings = useCallback((partial: Partial<Settings>) => {
    setSettingsState(persistSettings(partial));
  }, []);

  const reloadSettings = useCallback(() => {
    setSettingsState(getSettings());
  }, []);

  return (
    <SettingsContext.Provider
      value={{ settings, updateSettings, reloadSettings }}
    >
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings(): SettingsContextValue {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error("useSettings must be used within SettingsProvider");
  return ctx;
}
