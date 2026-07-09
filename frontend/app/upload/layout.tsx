"use client";

import type { ReactNode } from "react";
import { ChatThreadsProvider } from "@/lib/chat-threads-context";
import { useScratchTenant } from "@/lib/scratch-tenant-context";
import { AppSidebar } from "@/components/shell/app-sidebar";
import { MobileSidebarSheet } from "@/components/shell/mobile-sidebar-sheet";

export default function UploadLayout({ children }: { children: ReactNode }) {
  const { scratchTenantId } = useScratchTenant();

  const shell = (
    <div className="flex h-dvh flex-col md:flex-row">
      <aside className="hidden h-full w-[260px] shrink-0 flex-col border-r border-border bg-bg md:flex">
        <AppSidebar tenantId={scratchTenantId} />
      </aside>
      <MobileSidebarSheet tenantId={scratchTenantId} />
      <main className="flex flex-1 flex-col overflow-hidden">{children}</main>
    </div>
  );

  if (!scratchTenantId) return shell;

  return (
    <ChatThreadsProvider tenantId={scratchTenantId}>
      {shell}
    </ChatThreadsProvider>
  );
}
