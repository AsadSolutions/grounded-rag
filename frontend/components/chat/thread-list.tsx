"use client";

import { useState } from "react";
import { useChatThreads } from "@/lib/chat-threads-context";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { useToast } from "@/lib/toast-context";

export function ThreadList() {
  const {
    threads,
    activeThreadId,
    selectThread,
    renameThread,
    deleteThread,
    isStreamingActive,
  } = useChatThreads();
  const toast = useToast();
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

  function startRename(id: string, currentTitle: string) {
    setRenamingId(id);
    setRenameValue(currentTitle);
  }

  function commitRename() {
    if (renamingId && renameValue.trim().length > 0) {
      renameThread(renamingId, renameValue.trim());
    }
    setRenamingId(null);
  }

  const pendingDeleteThread = threads.find((t) => t.id === pendingDeleteId);

  return (
    <div className="flex flex-col gap-1">
      <button
        onClick={() => {
          if (isStreamingActive) return;
          selectThread(null);
        }}
        disabled={isStreamingActive}
        className="mb-2 flex cursor-pointer items-center gap-2 rounded-button border border-dashed border-border px-2 py-1.5 text-[13px] font-medium text-muted transition-colors duration-150 ease-out hover:bg-surface-2 hover:text-text disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:bg-transparent disabled:hover:text-muted"
      >
        <PlusIcon />
        New chat
      </button>

      {threads.length === 0 ? (
        <p className="px-2 py-4 text-[13px] text-muted">No chats yet.</p>
      ) : (
        threads.map((thread) => (
          <div
            key={thread.id}
            className={`group flex items-center gap-1 rounded-button px-2 py-1.5 ${
              thread.id === activeThreadId ? "bg-surface-2" : "hover:bg-surface-2"
            }`}
          >
            {renamingId === thread.id ? (
              <input
                autoFocus
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                onBlur={commitRename}
                onKeyDown={(e) => {
                  if (e.key === "Enter") commitRename();
                  if (e.key === "Escape") setRenamingId(null);
                }}
                className="flex-1 rounded-[4px] border border-border bg-surface px-1.5 py-0.5 text-[13px] text-text focus-visible:outline-none"
              />
            ) : (
              <button
                onClick={() => {
                  if (isStreamingActive) return;
                  selectThread(thread.id);
                }}
                disabled={isStreamingActive}
                title={thread.title}
                className={`flex-1 cursor-pointer truncate text-left text-[13px] disabled:cursor-not-allowed disabled:opacity-50 ${
                  thread.id === activeThreadId ? "text-accent" : "text-text"
                }`}
              >
                {thread.title}
              </button>
            )}
            <div className="hidden items-center gap-0.5 group-hover:flex">
              <button
                aria-label={`Rename ${thread.title}`}
                onClick={() => startRename(thread.id, thread.title)}
                className="cursor-pointer rounded-[4px] p-1 text-muted hover:bg-surface hover:text-text"
              >
                <PencilIcon />
              </button>
              <button
                aria-label={`Delete ${thread.title}`}
                onClick={() => setPendingDeleteId(thread.id)}
                className="cursor-pointer rounded-[4px] p-1 text-muted hover:bg-surface hover:text-danger"
              >
                <TrashIcon />
              </button>
            </div>
          </div>
        ))
      )}

      <ConfirmDialog
        open={pendingDeleteId !== null}
        title="Delete chat"
        description={`Delete "${pendingDeleteThread?.title ?? ""}"? This can't be undone.`}
        confirmLabel="Delete"
        destructive
        onConfirm={() => {
          if (pendingDeleteId) {
            const title = pendingDeleteThread?.title ?? "Chat";
            deleteThread(pendingDeleteId);
            toast.success(`Deleted "${title}"`);
          }
          setPendingDeleteId(null);
        }}
        onCancel={() => setPendingDeleteId(null)}
      />
    </div>
  );
}

function PlusIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M8 2v12M2 8h12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

function PencilIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M11 2l3 3-8 8-3.5.5.5-3.5 8-8z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M3 4h10M6.5 4V2.5h3V4M4.5 4l.5 9.5a1 1 0 001 1h4a1 1 0 001-1L11.5 4"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
