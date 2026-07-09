"use client";

import { useState } from "react";
import { useMediaQuery } from "@/lib/useMediaQuery";
import { SettingsPopover } from "./settings-popover";
import { SettingsSheet } from "./settings-sheet";

export function SettingsGear({ tenantId }: { tenantId: string | null }) {
  const isMobile = useMediaQuery("(max-width: 767px)");
  const [sheetOpen, setSheetOpen] = useState(false);

  const trigger = (
    <button
      aria-label="Settings"
      onClick={isMobile ? () => setSheetOpen(true) : undefined}
      className="flex size-9 cursor-pointer items-center justify-center rounded-button text-muted transition-colors duration-150 ease-out hover:bg-surface-2 hover:text-text"
    >
      <GearIcon />
    </button>
  );

  if (isMobile) {
    return (
      <>
        {trigger}
        <SettingsSheet
          tenantId={tenantId}
          open={sheetOpen}
          onClose={() => setSheetOpen(false)}
        />
      </>
    );
  }

  return <SettingsPopover tenantId={tenantId} trigger={trigger} />;
}

function GearIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r="2.5" stroke="currentColor" strokeWidth="1.3" />
      <path
        d="M8 1.5v1.4M8 13.1v1.4M14.5 8h-1.4M2.9 8H1.5M12.5 3.5l-1 1M4.5 11.5l-1 1M12.5 12.5l-1-1M4.5 4.5l-1-1"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}
