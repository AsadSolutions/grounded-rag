"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/input";
import { DropWell } from "@/components/upload/drop-well";
import {
  UploadFileRow,
  type UploadItem,
} from "@/components/upload/upload-file-row";
import { createTenant, uploadDocument } from "@/lib/api";
import { useScratchTenant } from "@/lib/scratch-tenant-context";

const REDIRECT_DELAY_MS = 600;

export default function UploadPage() {
  const router = useRouter();
  const { scratchTenantId, setScratchTenant } = useScratchTenant();
  const [workspaceName, setWorkspaceName] = useState("My workspace");
  const [items, setItems] = useState<UploadItem[]>([]);
  const itemsRef = useRef<UploadItem[]>([]);
  const creatingTenant = useRef<Promise<string> | null>(null);
  const redirected = useRef(false);
  const hasStarted = items.length > 0;

  function updateItems(updater: (prev: UploadItem[]) => UploadItem[]) {
    setItems((prev) => {
      const next = updater(prev);
      itemsRef.current = next;
      return next;
    });
  }

  async function resolveTenantId(): Promise<string> {
    if (scratchTenantId) return scratchTenantId;
    if (!creatingTenant.current) {
      const name = workspaceName.trim() || "My workspace";
      creatingTenant.current = createTenant().then((tenant) => {
        setScratchTenant(tenant.id, name);
        return tenant.id;
      });
    }
    return creatingTenant.current;
  }

  function maybeRedirect(tenantId: string) {
    if (redirected.current) return;
    const allTerminal =
      itemsRef.current.length > 0 &&
      itemsRef.current.every((item) => item.status !== "uploading");
    if (!allTerminal) return;
    redirected.current = true;
    setTimeout(() => router.push(`/chat/${tenantId}`), REDIRECT_DELAY_MS);
  }

  async function handleFilesAccepted(files: File[]) {
    const newItems: UploadItem[] = files.map((file) => ({
      id: crypto.randomUUID(),
      file,
      status: "uploading",
      progress: 0,
    }));
    updateItems((prev) => [...prev, ...newItems]);

    const tenantId = await resolveTenantId();

    await Promise.all(
      newItems.map(async (item) => {
        try {
          await uploadDocument(tenantId, item.file, (pct) => {
            updateItems((prev) =>
              prev.map((i) =>
                i.id === item.id ? { ...i, progress: pct } : i,
              ),
            );
          });
          updateItems((prev) =>
            prev.map((i) =>
              i.id === item.id ? { ...i, status: "done", progress: 100 } : i,
            ),
          );
        } catch (error) {
          updateItems((prev) =>
            prev.map((i) =>
              i.id === item.id
                ? {
                    ...i,
                    status: "failed",
                    error:
                      error instanceof Error
                        ? error.message
                        : "Upload failed.",
                  }
                : i,
            ),
          );
        }
      }),
    );

    maybeRedirect(tenantId);
  }

  return (
    <div className="mx-auto flex w-full max-w-content flex-1 flex-col gap-6 px-4 py-10 sm:px-6 sm:py-16">
      <div className="flex flex-col gap-2">
        <h1 className="font-serif text-title text-text">Upload documents</h1>
        <p className="text-body leading-reading text-muted">
          Add PDF, TXT, or MD files to ask questions about them.
        </p>
      </div>

      {!scratchTenantId && (
        <div className="flex max-w-upload-well flex-col gap-1.5">
          <label
            htmlFor="workspace-name"
            className="text-caption font-medium text-text"
          >
            Workspace name <span className="text-muted">(optional)</span>
          </label>
          <Input
            id="workspace-name"
            value={workspaceName}
            onChange={(e) => setWorkspaceName(e.target.value)}
            placeholder="My workspace"
            disabled={hasStarted}
          />
        </div>
      )}

      <DropWell onFilesAccepted={handleFilesAccepted} />

      <p className="text-caption leading-reading text-muted">
        Your workspace is temporary and expires 24 hours after creation.
        Documents are processed and stored for retrieval.
      </p>

      {items.length > 0 && (
        <ul className="flex flex-col gap-2">
          {items.map((item) => (
            <UploadFileRow key={item.id} item={item} />
          ))}
        </ul>
      )}
    </div>
  );
}
