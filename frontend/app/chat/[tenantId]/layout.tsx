import type { ReactNode } from "react";
import { ChatThreadsProvider } from "@/lib/chat-threads-context";
import { AppSidebar } from "@/components/shell/app-sidebar";
import { MobileSidebarSheet } from "@/components/shell/mobile-sidebar-sheet";

export default async function ChatTenantLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Promise<{ tenantId: string }>;
}) {
  const { tenantId } = await params;

  return (
    <ChatThreadsProvider tenantId={tenantId}>
      <div className="flex h-dvh flex-col md:flex-row">
        <aside className="hidden h-full w-[260px] shrink-0 flex-col border-r border-border bg-bg md:flex">
          <AppSidebar tenantId={tenantId} />
        </aside>
        <MobileSidebarSheet tenantId={tenantId} />
        <main className="flex flex-1 flex-col overflow-hidden">{children}</main>
      </div>
    </ChatThreadsProvider>
  );
}
