import type { ReactElement } from "react";
import { Popover } from "@/components/ui/popover";
import { SettingsPanel } from "./settings-panel";

export function SettingsPopover({
  tenantId,
  trigger,
}: {
  tenantId: string | null;
  trigger: ReactElement<{ onClick?: () => void }>;
}) {
  return (
    <Popover trigger={trigger} align="start" placement="top" variant="wide">
      <SettingsPanel tenantId={tenantId} />
    </Popover>
  );
}
