"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { deleteDocument } from "@/lib/api";
import { useMediaQuery } from "@/lib/useMediaQuery";
import { useChatThreads } from "@/lib/chat-threads-context";
import { useToast } from "@/lib/toast-context";
import type { Document } from "@/lib/types";

export function DocumentsPanel({
  tenantId,
  documents,
  isDemo,
}: {
  tenantId: string;
  documents: Document[];
  isDemo: boolean;
}) {
  const { activeThread } = useChatThreads();
  const toast = useToast();
  const [items, setItems] = useState(documents);
  const [pendingDelete, setPendingDelete] = useState<Document | null>(null);
  const [collapsed, setCollapsed] = useState(true);
  const [mounted, setMounted] = useState(false);
  const isNarrow = useMediaQuery("(max-width: 1100px)");

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  const lastAnswer = [...(activeThread?.messages ?? [])]
    .reverse()
    .find((m) => m.role === "assistant" && !m.error);
  const citedDocIds = new Set(
    lastAnswer && lastAnswer.role === "assistant"
      ? lastAnswer.sources.map((s) => s.docId)
      : [],
  );

  async function handleDelete() {
    if (!pendingDelete) return;
    const { id, name } = pendingDelete;
    try {
      await deleteDocument(tenantId, id);
      setItems((prev) => prev.filter((d) => d.id !== id));
      setPendingDelete(null);
      toast.success(`Deleted "${name}"`);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to delete document";
      toast.error(message);
    }
  }

  const displayNarrowMode = isNarrow && collapsed;

  if (displayNarrowMode) {
    return (
      <button
        onClick={() => setCollapsed(false)}
        className="fixed bottom-6 right-6 z-30 cursor-pointer rounded-button border border-border bg-surface px-4 py-2 text-[13px] font-medium text-text shadow-[var(--shadow-card)]"
      >
        Documents ({items.length})
      </button>
    );
  }

  return (
    <aside
      className={`flex h-full w-[300px] shrink-0 flex-col gap-4 border-l border-border bg-surface p-4 ${
        isNarrow ? "fixed inset-y-0 right-0 z-30" : ""
      }`}
    >
      <div className="flex items-center justify-between">
        <h2 className="font-serif text-[20px] text-text">Documents</h2>
        {isNarrow && (
          <button
            onClick={() => setCollapsed(true)}
            aria-label="Collapse documents panel"
            className="cursor-pointer text-muted transition-colors duration-150 ease-out hover:text-text"
          >
            <CloseIcon />
          </button>
        )}
      </div>
      {items.length === 0 ? (
        <p className="text-[15px] leading-[1.6] text-muted">
          No documents yet. Add some to start asking.
        </p>
      ) : (
        <ul className="flex flex-col gap-2 overflow-y-auto">
          {items.map((doc) => (
            <li
              key={doc.id}
              className={`group rounded-card border border-border bg-bg p-3 ${
                citedDocIds.has(doc.id) ? "border-l-2 border-l-accent" : ""
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-[14px] font-medium text-text">{doc.name}</p>
                {!isDemo && (
                  <button
                    onClick={() => setPendingDelete(doc)}
                    aria-label={`Delete ${doc.name}`}
                    className="shrink-0 cursor-pointer text-muted opacity-0 transition-opacity duration-150 ease-out hover:text-danger group-hover:opacity-100"
                  >
                    <TrashIcon />
                  </button>
                )}
              </div>
              <p className="mt-1 text-[13px] text-muted">
                {doc.chunkCount} chunks ·{" "}
                {doc.uploadedAt
                  ? new Date(doc.uploadedAt).toLocaleDateString()
                  : "seeded"}
              </p>
            </li>
          ))}
        </ul>
      )}
      {!isDemo && (
        <Button
          href={`/upload?tenant=${tenantId}`}
          variant="ghost"
          className="mt-auto"
        >
          Add documents
        </Button>
      )}
      <ConfirmDialog
        open={pendingDelete !== null}
        title="Delete document"
        description={`Delete "${pendingDelete?.name ?? ""}"? This can't be undone.`}
        confirmLabel="Delete"
        destructive
        onConfirm={handleDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </aside>
  );
}

function CloseIcon() {
  return (
    <svg
      width="14"
      height="14"
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

function TrashIcon() {
  return (
    <svg
      width="14"
      height="14"
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
