"use client";

import type { ReactNode } from "react";
import { ChatThreadsProvider } from "@/lib/chat-threads-context";
import { useScratchTenant } from "@/lib/scratch-tenant-context";
import { useLastVisitedTenantId } from "@/lib/use-last-visited-tenant";
import { AppSidebar } from "@/components/shell/app-sidebar";
import { MobileSidebarSheet } from "@/components/shell/mobile-sidebar-sheet";

export default function UploadLayout({ children }: { children: ReactNode }) {
  const { scratchTenantId } = useScratchTenant();
  const lastVisitedTenantId = useLastVisitedTenantId();
  const sidebarTenantId = lastVisitedTenantId ?? scratchTenantId;

  const shell = (
    <div className="flex h-dvh flex-col md:flex-row">
      <aside className="hidden h-full w-sidebar shrink-0 flex-col border-r border-border bg-bg md:flex">
        <AppSidebar tenantId={sidebarTenantId} />
      </aside>
      <MobileSidebarSheet tenantId={sidebarTenantId} />
      <main className="flex flex-1 flex-col overflow-hidden">{children}</main>
    </div>
  );

  if (!sidebarTenantId) return shell;

  return (
    <ChatThreadsProvider tenantId={sidebarTenantId}>
      {shell}
    </ChatThreadsProvider>
  );
}
