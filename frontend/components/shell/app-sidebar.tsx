import Link from "next/link";
import { Nav } from "./nav";
import { TenantSwitcher } from "./tenant-switcher";
import { SettingsGear } from "./settings-gear";
import { ThreadList } from "@/components/chat/thread-list";

export function AppSidebar({
  tenantId,
  inSheet = false,
}: {
  tenantId: string | null;
  inSheet?: boolean;
}) {
  return (
    <div className="flex h-full flex-col">
      {!inSheet && (
        <div className="flex items-center gap-2 px-4 py-4">
          <Link href="/" className="flex items-center gap-2">
            <span className="font-serif text-[16px] font-semibold text-text">
              Grounded<span className="text-accent">RAG</span>
            </span>
          </Link>
        </div>
      )}
      <div className="px-3 pt-2">
        <TenantSwitcher tenantId={tenantId} />
      </div>
      <div className="mt-2 px-3">
        <Nav tenantId={tenantId} />
      </div>
      <div className="mt-4 flex-1 overflow-y-auto px-3">
        {tenantId ? (
          <ThreadList />
        ) : (
          <p className="px-2 py-4 text-[13px] text-muted">
            Upload documents to start chatting.
          </p>
        )}
      </div>
      <div className="p-3">
        <SettingsGear tenantId={tenantId} />
      </div>
    </div>
  );
}
