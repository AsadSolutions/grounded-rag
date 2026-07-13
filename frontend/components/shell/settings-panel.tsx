"use client";

import { useState } from "react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { clearAllLocalData } from "@/lib/settings";
import { useSettings } from "@/lib/settings-context";

export function SettingsPanel({ tenantId }: { tenantId: string | null }) {
  const { settings, updateSettings } = useSettings();
  const [confirmClear, setConfirmClear] = useState(false);

  function handleClear() {
    clearAllLocalData(tenantId);
    setConfirmClear(false);
    window.location.reload();
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <p className="text-eyebrow font-medium uppercase tracking-eyebrow text-muted">
          Theme
        </p>
        <ThemeToggle />
      </div>
      <SettingsToggleRow
        label="Streaming"
        checked={settings.streaming}
        onChange={() => updateSettings({ streaming: !settings.streaming })}
      />
      <SettingsToggleRow
        label="Show reasoning by default"
        checked={settings.showReasoningByDefault}
        onChange={() =>
          updateSettings({
            showReasoningByDefault: !settings.showReasoningByDefault,
          })
        }
      />
      <div className="flex flex-col gap-2">
        <p className="text-eyebrow font-medium uppercase tracking-eyebrow text-muted">
          Density
        </p>
        <div className="flex w-full rounded-button border border-border p-0.5">
          {(["comfortable", "compact"] as const).map((option) => (
            <button
              key={option}
              onClick={() => updateSettings({ density: option })}
              aria-pressed={settings.density === option}
              className={`flex-1 cursor-pointer rounded-control px-3 py-1.5 text-center text-caption font-medium capitalize transition-colors duration-150 ease-out ${
                settings.density === option
                  ? "bg-accent text-white"
                  : "text-muted hover:text-text"
              }`}
            >
              {option}
            </button>
          ))}
        </div>
      </div>
      <Button variant="danger" onClick={() => setConfirmClear(true)}>
        Clear local data
      </Button>
      <ConfirmDialog
        open={confirmClear}
        title="Clear local data"
        description="This removes your streaming, reasoning, and density preferences and every saved chat thread for this tenant. Your theme is not affected. This can't be undone."
        confirmLabel="Clear data"
        destructive
        onConfirm={handleClear}
        onCancel={() => setConfirmClear(false)}
      />
    </div>
  );
}

function SettingsToggleRow({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-text">{label}</span>
      <button
        role="switch"
        aria-checked={checked}
        onClick={onChange}
        className={`flex h-6 w-10 shrink-0 cursor-pointer items-center rounded-full p-0.5 transition-colors duration-150 ease-out ${
          checked ? "bg-accent" : "bg-surface-2"
        }`}
      >
        <span
          className={`size-5 shrink-0 rounded-full bg-surface transition-[margin-left] duration-150 ease-out ${
            checked ? "ml-4" : "ml-0"
          }`}
        />
      </button>
    </div>
  );
}
