"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { API_BASE_URL } from "@/lib/real-api";

const CONNECTIVITY_PATTERNS = [
  "fetch failed",
  "failed to fetch",
  "econnrefused",
  "network error",
  "networkerror",
];

function isConnectivityError(message: string): boolean {
  const lower = message.toLowerCase();
  return CONNECTIVITY_PATTERNS.some((pattern) => lower.includes(pattern));
}

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  const connectivityIssue = isConnectivityError(error.message);

  return (
    <div className="mx-auto flex w-full max-w-content flex-1 flex-col items-center justify-center gap-6 px-6 py-24 text-center">
      <div className="flex max-w-[520px] flex-col gap-4 rounded-card border border-border bg-surface p-8">
        <h1 className="font-serif text-[20px] text-text">
          {connectivityIssue
            ? "Can't reach the GroundedRAG API"
            : "Something went wrong"}
        </h1>
        <p className="text-[15px] leading-[1.6] text-muted">
          {connectivityIssue ? (
            <>
              The backend at{" "}
              <code className="rounded-button bg-surface-2 px-1.5 py-0.5 font-mono text-[13px] text-text">
                {API_BASE_URL}
              </code>{" "}
              didn&apos;t respond. If you&apos;re running this locally, make
              sure the FastAPI server is started (
              <code className="rounded-button bg-surface-2 px-1.5 py-0.5 font-mono text-[13px] text-text">
                uvicorn app.main:app --reload
              </code>
              ) and Qdrant is up (
              <code className="rounded-button bg-surface-2 px-1.5 py-0.5 font-mono text-[13px] text-text">
                docker compose up -d qdrant
              </code>
              ).
            </>
          ) : (
            error.message
          )}
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
          <Button variant="primary" onClick={reset}>
            Try again
          </Button>
          <Button href="/" variant="ghost">
            Back to home
          </Button>
        </div>
      </div>
    </div>
  );
}
