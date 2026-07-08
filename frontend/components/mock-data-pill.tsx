import { Badge } from "@/components/ui/badge";

/** Persistent footer indicator, shown only when the app is serving mock data. */
export function MockDataPill() {
  if (process.env.NEXT_PUBLIC_USE_MOCKS !== "true") {
    return null;
  }

  return (
    <div className="fixed bottom-4 left-4 z-50">
      <Badge variant="warn">Mock data</Badge>
    </div>
  );
}
