"use client";

import { useTheme } from "./theme-provider";
import type { ThemePreference } from "@/lib/theme";

const options: { value: ThemePreference; label: string }[] = [
  { value: "system", label: "System" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];

export function ThemeToggle() {
  const { preference, setPreference } = useTheme();

  return (
    <div className="flex w-full rounded-button border border-border p-0.5">
      {options.map((option) => (
        <button
          key={option.value}
          onClick={() => setPreference(option.value)}
          aria-pressed={preference === option.value}
          className={`flex-1 cursor-pointer rounded-control px-3 py-1.5 text-center text-caption font-medium transition-colors duration-150 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
            preference === option.value
              ? "bg-accent text-white"
              : "text-muted hover:text-text"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
