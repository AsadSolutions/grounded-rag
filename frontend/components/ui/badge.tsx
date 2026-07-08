import type { HTMLAttributes } from "react";

type BadgeVariant = "ok" | "warn" | "danger";

const dotColor: Record<BadgeVariant, string> = {
  ok: "bg-ok",
  warn: "bg-warn",
  danger: "bg-danger",
};

const textColor: Record<BadgeVariant, string> = {
  ok: "text-ok",
  warn: "text-warn",
  danger: "text-danger",
};

type BadgeProps = HTMLAttributes<HTMLSpanElement> & {
  variant: BadgeVariant;
};

export function Badge({
  variant,
  className = "",
  children,
  ...props
}: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-button bg-surface-2 px-2 py-1 text-[13px] font-medium ${textColor[variant]} ${className}`.trim()}
      {...props}
    >
      <span
        className={`size-1.5 rounded-full ${dotColor[variant]}`}
        aria-hidden="true"
      />
      {children}
    </span>
  );
}
