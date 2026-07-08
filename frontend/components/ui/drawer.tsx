"use client";

import type { ReactNode } from "react";
import { useFocusTrap } from "./use-focus-trap";

type DrawerProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
};

export function Drawer({ open, onClose, title, children }: DrawerProps) {
  const containerRef = useFocusTrap(open, onClose);

  return (
    <div
      className={`fixed inset-0 z-50 ${open ? "" : "pointer-events-none"}`}
      aria-hidden={!open}
    >
      <div
        onClick={onClose}
        className={`absolute inset-0 bg-black/30 transition-opacity duration-150 ease-out ${
          open ? "opacity-100" : "opacity-0"
        }`}
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        inert={!open}
        className={`absolute right-0 top-0 h-full w-[420px] max-w-[90vw] border-l border-border bg-surface transition-transform duration-150 ease-out focus:outline-none ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="font-serif text-[18px] text-text">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded-button p-1.5 text-muted transition-colors duration-150 ease-out hover:bg-surface-2 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            <CloseIcon />
          </button>
        </div>
        <div className="h-[calc(100%-61px)] overflow-y-auto p-5">
          {children}
        </div>
      </div>
    </div>
  );
}

function CloseIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M4 4L12 12M12 4L4 12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
