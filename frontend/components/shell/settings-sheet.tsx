"use client";

import { Drawer } from "@/components/ui/drawer";
import { SettingsPanel } from "./settings-panel";

export function SettingsSheet({
  tenantId,
  open,
  onClose,
}: {
  tenantId: string | null;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <Drawer open={open} onClose={onClose} title="Settings" side="bottom">
      <SettingsPanel tenantId={tenantId} />
    </Drawer>
  );
}
