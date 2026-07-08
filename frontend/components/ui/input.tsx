import type { InputHTMLAttributes } from "react";

export function Input({
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`w-full rounded-card border border-border bg-surface px-3 py-2 text-[15px] text-text placeholder:text-muted transition-colors duration-150 ease-out focus-visible:outline-none focus-visible:border-muted disabled:opacity-50 ${className}`.trim()}
      {...props}
    />
  );
}
