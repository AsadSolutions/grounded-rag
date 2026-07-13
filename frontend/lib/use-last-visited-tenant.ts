"use client";

import { useEffect, useState } from "react";
import { getLastVisitedTenantId } from "@/lib/tenant";

export function useLastVisitedTenantId(): string | null {
  const [tenantId, setTenantId] = useState<string | null>(null);

  useEffect(() => {
    setTenantId(getLastVisitedTenantId());
  }, []);

  return tenantId;
}
