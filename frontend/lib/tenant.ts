export const CURRENT_TENANT_ID_STORAGE_KEY = "groundedrag-current-tenant-id";

function tenantNameKey(tenantId: string): string {
  return `groundedrag-tenant-name-${tenantId}`;
}

export function getStoredTenantName(tenantId: string): string | null {
  return window.localStorage.getItem(tenantNameKey(tenantId));
}

export function getStoredScratchTenantId(): string | null {
  return window.localStorage.getItem(CURRENT_TENANT_ID_STORAGE_KEY);
}

export function storeScratchTenant(tenantId: string, name: string): void {
  window.localStorage.setItem(CURRENT_TENANT_ID_STORAGE_KEY, tenantId);
  window.localStorage.setItem(tenantNameKey(tenantId), name);
}

export function clearStoredTenantPointer(): void {
  window.localStorage.removeItem(CURRENT_TENANT_ID_STORAGE_KEY);
}
