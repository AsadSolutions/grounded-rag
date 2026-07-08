"use client";

import {
  cloneElement,
  isValidElement,
  useEffect,
  useRef,
  useState,
  type ReactElement,
  type ReactNode,
} from "react";

type PopoverProps = {
  trigger: ReactElement<{ onClick?: () => void }>;
  children: ReactNode;
  align?: "start" | "end";
};

export function Popover({ trigger, children, align = "start" }: PopoverProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(e: PointerEvent) {
      if (rootRef.current?.contains(e.target as Node)) return;
      setOpen(false);
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      setOpen(false);
      rootRef.current
        ?.querySelector<HTMLElement>("button, a, [tabindex]")
        ?.focus();
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const triggerElement = isValidElement(trigger)
    ? cloneElement(trigger, { onClick: () => setOpen((v) => !v) })
    : trigger;

  return (
    <div ref={rootRef} className="relative inline-block">
      {triggerElement}
      {open && (
        <div
          role="dialog"
          className={`absolute top-[calc(100%+8px)] z-40 min-w-[200px] rounded-card border border-border bg-surface p-3 shadow-[var(--shadow-card)] transition-all duration-150 ease-out ${
            align === "end" ? "right-0" : "left-0"
          }`}
        >
          {children}
        </div>
      )}
    </div>
  );
}
