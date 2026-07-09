"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  clearStoredTenantPointer,
  getStoredScratchTenantId,
  getStoredTenantName,
  storeScratchTenant,
} from "@/lib/tenant";

type ScratchTenantContextValue = {
  scratchTenantId: string | null;
  scratchTenantName: string | null;
  setScratchTenant: (tenantId: string, name: string) => void;
  clearScratchTenant: () => void;
};

const ScratchTenantContext = createContext<ScratchTenantContextValue | null>(
  null,
);

export function ScratchTenantProvider({ children }: { children: ReactNode }) {
  const [scratchTenantId, setScratchTenantId] = useState<string | null>(null);
  const [scratchTenantName, setScratchTenantName] = useState<string | null>(
    null,
  );

  useEffect(() => {
    const id = getStoredScratchTenantId();
    setScratchTenantId(id);
    setScratchTenantName(id ? getStoredTenantName(id) : null);
  }, []);

  const setScratchTenant = useCallback((tenantId: string, name: string) => {
    storeScratchTenant(tenantId, name);
    setScratchTenantId(tenantId);
    setScratchTenantName(name);
  }, []);

  const clearScratchTenant = useCallback(() => {
    clearStoredTenantPointer();
    setScratchTenantId(null);
    setScratchTenantName(null);
  }, []);

  return (
    <ScratchTenantContext.Provider
      value={{
        scratchTenantId,
        scratchTenantName,
        setScratchTenant,
        clearScratchTenant,
      }}
    >
      {children}
    </ScratchTenantContext.Provider>
  );
}

export function useScratchTenant(): ScratchTenantContextValue {
  const ctx = useContext(ScratchTenantContext);
  if (!ctx) {
    throw new Error(
      "useScratchTenant must be used within ScratchTenantProvider",
    );
  }
  return ctx;
}
