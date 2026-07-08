export type ThemePreference = "system" | "light" | "dark";

export const THEME_STORAGE_KEY = "groundedrag-theme";

export function getStoredTheme(): ThemePreference {
  const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
  return stored === "light" || stored === "dark" || stored === "system"
    ? stored
    : "system";
}

export function resolveTheme(preference: ThemePreference): "light" | "dark" {
  if (preference === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }
  return preference;
}

export function applyTheme(preference: ThemePreference) {
  document.documentElement.classList.toggle(
    "dark",
    resolveTheme(preference) === "dark",
  );
}

export const THEME_INIT_SCRIPT = `(function(){try{var k='${THEME_STORAGE_KEY}';var s=localStorage.getItem(k);var t=s==='light'||s==='dark'||s==='system'?s:'system';var d=t==='system'?window.matchMedia('(prefers-color-scheme: dark)').matches:(t==='dark');if(d)document.documentElement.classList.add('dark');}catch(e){}})();`;
