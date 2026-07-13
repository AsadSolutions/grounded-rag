"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Popover } from "@/components/ui/popover";
import { getDemoTenants } from "@/lib/api";
import { useScratchTenant } from "@/lib/scratch-tenant-context";
import type { DemoTenant } from "@/lib/types";

export function TenantSwitcher({ tenantId }: { tenantId: string | null }) {
  const [demoTenants, setDemoTenants] = useState<DemoTenant[]>([]);
  const { scratchTenantId, scratchTenantName } = useScratchTenant();

  useEffect(() => {
    getDemoTenants().then(setDemoTenants);
  }, []);

  const currentDemo = demoTenants.find((t) => t.id === tenantId);
  const isScratchActive = tenantId !== null && tenantId === scratchTenantId;

  const currentName =
    currentDemo?.name ??
    (isScratchActive ? scratchTenantName : null) ??
    "Select a tenant";

  return (
    <Popover
      trigger={
        <button className="flex w-full cursor-pointer items-center justify-between rounded-button px-2 py-1.5 text-sm font-medium text-text transition-colors duration-150 ease-out hover:bg-surface-2">
          <span className="truncate pr-1">{currentName}</span>
          <ChevronIcon />
        </button>
      }
      variant="medium"
    >
      <div className="flex flex-col">
        {scratchTenantId && (
          <div className="mb-2 flex flex-col gap-0.5">
            <p className="px-2 pb-1 text-eyebrow font-medium uppercase tracking-eyebrow text-muted">
              Your workspace
            </p>
            <Link
              href={`/chat/${scratchTenantId}`}
              className={`flex flex-col gap-0.5 rounded-button px-2 py-1.5 transition-colors duration-150 ease-out hover:bg-surface-2 ${
                isScratchActive ? "bg-accent-soft text-accent" : "text-text"
              }`}
            >
              <span className="truncate text-sm">
                {scratchTenantName ?? "My workspace"}
              </span>
              <span className="text-xs text-muted">
                temporary, expires 24h
              </span>
            </Link>
          </div>
        )}

        <p className="px-2 pb-1 text-eyebrow font-medium uppercase tracking-eyebrow text-muted">
          Demo tenants
        </p>
        <div className="flex flex-col gap-0.5">
          {demoTenants.map((tenant) => (
            <Link
              key={tenant.id}
              href={`/chat/${tenant.id}`}
              className={`rounded-button px-2 py-1.5 text-sm transition-colors duration-150 ease-out hover:bg-surface-2 ${
                tenant.id === tenantId
                  ? "bg-accent-soft text-accent"
                  : "text-text"
              }`}
            >
              {tenant.name}
            </Link>
          ))}
        </div>

        <div className="mt-2 border-t border-border pt-2">
          <Link
            href="/upload"
            className="block rounded-button px-2 py-1.5 text-sm font-medium text-accent transition-colors duration-150 ease-out hover:bg-surface-2"
          >
            Upload your own documents
          </Link>
        </div>
      </div>
    </Popover>
  );
}

function ChevronIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 16 16"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M4 6l4 4 4-4"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
