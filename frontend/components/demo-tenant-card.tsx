import Link from "next/link";
import { Card } from "@/components/ui/card";
import type { DemoTenant } from "@/lib/types";

export function DemoTenantCard({ tenant }: { tenant: DemoTenant }) {
  return (
    <Link href={`/chat/${tenant.id}`} className="block h-full">
      <Card className="flex h-full flex-col gap-3 transition-colors duration-150 ease-out hover:bg-surface-2">
        <div className="flex items-start justify-between gap-3">
          <h3 className="font-serif text-xl text-text">{tenant.name}</h3>
          <span className="shrink-0 text-caption text-muted">
            {tenant.documentCount} documents
          </span>
        </div>
        <p className="text-body leading-reading text-muted">
          {tenant.description}
        </p>
        <p className="mt-auto text-body italic text-muted">
          &ldquo;{tenant.suggestedQuestion}&rdquo;
        </p>
      </Card>
    </Link>
  );
}
