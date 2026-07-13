export type ToastVariant = "success" | "error";

export function Toast({
  variant,
  message,
  onDismiss,
}: {
  variant: ToastVariant;
  message: string;
  onDismiss: () => void;
}) {
  return (
    <div
      role="status"
      className="animate-fade-slide-in pointer-events-auto flex items-center gap-2.5 rounded-card border border-border bg-surface px-4 py-3 text-sm text-text shadow-card"
    >
      <span
        className={variant === "success" ? "text-ok" : "text-danger"}
        aria-hidden="true"
      >
        {variant === "success" ? <CheckIcon /> : <ErrorIcon />}
      </span>
      <span className="max-w-toast">{message}</span>
      <button
        onClick={onDismiss}
        aria-label="Dismiss"
        className="ml-1 cursor-pointer rounded p-0.5 text-muted transition-colors duration-150 ease-out hover:bg-surface-2 hover:text-text"
      >
        <CloseIcon />
      </button>
    </div>
  );
}

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M3 8.5l3 3 7-7"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ErrorIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="6.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M8 5v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="8" cy="11" r="0.75" fill="currentColor" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M4 4L12 12M12 4L4 12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
