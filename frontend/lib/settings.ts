import { clearThreads } from "@/lib/threads";
import { clearStoredTenantPointer } from "@/lib/tenant";

export type Density = "comfortable" | "compact";

export type Settings = {
  streaming: boolean;
  showReasoningByDefault: boolean;
  density: Density;
};

const SETTINGS_STORAGE_KEY = "groundedrag-settings";

export const DEFAULT_SETTINGS: Settings = {
  streaming: true,
  showReasoningByDefault: false,
  density: "comfortable",
};

export function getSettings(): Settings {
  const raw = window.localStorage.getItem(SETTINGS_STORAGE_KEY);
  if (!raw) return DEFAULT_SETTINGS;
  return { ...DEFAULT_SETTINGS, ...(JSON.parse(raw) as Partial<Settings>) };
}

export function setSettings(partial: Partial<Settings>): Settings {
  const next = { ...getSettings(), ...partial };
  window.localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(next));
  return next;
}

export function clearAllLocalData(tenantId: string | null): void {
  window.localStorage.removeItem(SETTINGS_STORAGE_KEY);
  if (tenantId) clearThreads(tenantId);
  clearStoredTenantPointer();
}
