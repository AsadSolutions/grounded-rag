"use client";

import type { ReactNode } from "react";
import { useFocusTrap } from "./use-focus-trap";

type DrawerSide = "right" | "left" | "bottom";

type DrawerProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  side?: DrawerSide;
};

const sidePositionClasses: Record<DrawerSide, string> = {
  right: "right-0 top-0 h-full w-drawer max-w-[90vw] border-l",
  left: "left-0 top-0 h-full w-mobile-sheet max-w-[85vw] border-r",
  bottom: "bottom-0 left-0 w-full max-h-[85vh] border-t",
};

const sideTransformClasses: Record<DrawerSide, { open: string; closed: string }> = {
  right: { open: "translate-x-0", closed: "translate-x-full" },
  left: { open: "translate-x-0", closed: "-translate-x-full" },
  bottom: { open: "translate-y-0", closed: "translate-y-full" },
};

const sideContentClasses: Record<DrawerSide, string> = {
  right: "h-[calc(100%-var(--spacing-drawer-header))] overflow-y-auto p-5",
  left: "h-[calc(100%-var(--spacing-drawer-header))] overflow-y-auto p-5",
  bottom: "max-h-[calc(85vh-var(--spacing-drawer-header))] overflow-y-auto p-5",
};

export function Drawer({
  open,
  onClose,
  title,
  children,
  side = "right",
}: DrawerProps) {
  const containerRef = useFocusTrap(open, onClose);
  const transform = sideTransformClasses[side];

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
        className={`absolute border-border bg-surface transition-transform duration-150 ease-out focus:outline-none ${
          sidePositionClasses[side]
        } ${open ? transform.open : transform.closed}`}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="font-serif text-lg text-text">{title}</h2>
          <button
            onClick={onClose}
            aria-label="Close"
            className="cursor-pointer rounded-button p-1.5 text-muted transition-colors duration-150 ease-out hover:bg-surface-2 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          >
            <CloseIcon />
          </button>
        </div>
        <div className={sideContentClasses[side]}>{children}</div>
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
