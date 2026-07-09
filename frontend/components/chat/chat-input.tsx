"use client";

import { useEffect, useRef, type KeyboardEvent } from "react";

const MAX_HEIGHT = 200;

type ChatInputProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
};

export function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = "Ask a question...",
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const canSend = !disabled && value.trim().length > 0;

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_HEIGHT)}px`;
  }, [value]);

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (canSend) onSubmit();
    }
  }

  return (
    <div className="flex w-full flex-col gap-2 rounded-card border border-border bg-surface px-4 py-3 shadow-[var(--shadow-card)] transition-colors duration-150 ease-out focus-within:border-muted">
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={placeholder}
        className="max-h-[200px] w-full resize-none bg-transparent text-[15px] text-text placeholder:text-muted focus-visible:outline-none disabled:opacity-50"
      />
      <div className="flex items-center justify-end">
        <button
          type="button"
          aria-label="Send message"
          onClick={() => canSend && onSubmit()}
          disabled={!canSend}
          className="flex size-9 shrink-0 cursor-pointer items-center justify-center rounded-button bg-accent text-white transition-colors duration-150 ease-out hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <SendIcon />
        </button>
      </div>
    </div>
  );
}

function SendIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M8 13V3M8 3L3.5 7.5M8 3l4.5 4.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
