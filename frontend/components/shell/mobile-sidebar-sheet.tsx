"use client";

import { useState } from "react";
import { Drawer } from "@/components/ui/drawer";
import { AppSidebar } from "./app-sidebar";

export function MobileSidebarSheet({ tenantId }: { tenantId: string | null }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className="flex items-center justify-between border-b border-border px-4 py-3 md:hidden">
        <button
          aria-label="Open menu"
          onClick={() => setOpen(true)}
          className="flex size-9 cursor-pointer items-center justify-center rounded-button text-muted transition-colors duration-150 ease-out hover:bg-surface-2 hover:text-text"
        >
          <MenuIcon />
        </button>
        <span className="font-serif text-body font-semibold text-text">
          Grounded<span className="text-accent">RAG</span>
        </span>
        <span className="size-9" aria-hidden="true" />
      </div>
      <Drawer
        open={open}
        onClose={() => setOpen(false)}
        title="Menu"
        side="left"
      >
        <AppSidebar tenantId={tenantId} inSheet />
      </Drawer>
    </>
  );
}

function MenuIcon() {
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M2 4h12M2 8h12M2 12h12"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}
