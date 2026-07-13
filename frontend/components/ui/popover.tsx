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
  placement?: "top" | "bottom";
  variant?: "default" | "wide" | "medium";
};

export function Popover({
  trigger,
  children,
  align = "start",
  placement = "bottom",
  variant = "default",
}: PopoverProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);
  const wasOpenRef = useRef(false);

  useEffect(() => {
    if (!open) return;
    triggerRef.current = rootRef.current?.querySelector<HTMLElement>(
      "button, a, [tabindex]",
    ) ?? null;
    wasOpenRef.current = true;

    function handlePointerDown(e: PointerEvent) {
      if (rootRef.current?.contains(e.target as Node)) return;
      setOpen(false);
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key !== "Escape") return;
      setOpen(false);
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  useEffect(() => {
    if (open || !wasOpenRef.current) return;
    triggerRef.current?.focus();
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
          className={`absolute z-40 ${
            variant === "wide"
              ? "w-popover-wide"
              : variant === "medium"
                ? "w-popover-medium"
                : "min-w-popover"
          } overflow-hidden rounded-card border border-border bg-surface p-3 shadow-card transition-all duration-150 ease-out ${
            placement === "top" ? "bottom-[calc(100%+8px)]" : "top-[calc(100%+8px)]"
          } ${align === "end" ? "right-0" : "left-0"}`}
        >
          {children}
        </div>
      )}
    </div>
  );
}
