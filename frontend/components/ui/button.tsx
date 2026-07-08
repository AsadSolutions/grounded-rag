import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

const base =
  "inline-flex items-center justify-center gap-2 rounded-button px-4 py-2 text-[14px] font-medium transition-colors duration-150 ease-out disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg";

const variants: Record<ButtonVariant, string> = {
  primary: "bg-accent text-white hover:bg-accent/90",
  secondary: "border border-border bg-transparent text-text hover:bg-surface-2",
  ghost: "bg-transparent text-text hover:bg-surface-2",
  danger: "bg-danger text-white hover:bg-danger/90",
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonProps) {
  return (
    <button
      className={`${base} ${variants[variant]} ${className}`.trim()}
      {...props}
    />
  );
}
