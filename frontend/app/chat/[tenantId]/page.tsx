import { getDemoTenants, listDocuments } from "@/lib/api";
import { ChatPanel } from "@/components/chat/chat-panel";
import { DocumentsPanel } from "@/components/documents/documents-panel";

export default async function ChatPage({
  params,
}: {
  params: Promise<{ tenantId: string }>;
}) {
  const { tenantId } = await params;
  const [documents, demoTenants] = await Promise.all([
    listDocuments(tenantId),
    getDemoTenants(),
  ]);
  const isDemo = demoTenants.find((t) => t.id === tenantId)?.isDemo ?? false;

  return (
    <div className="flex flex-1 overflow-hidden">
      <ChatPanel tenantId={tenantId} />
      <DocumentsPanel tenantId={tenantId} documents={documents} isDemo={isDemo} />
    </div>
  );
}
