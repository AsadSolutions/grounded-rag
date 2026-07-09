import { Badge } from "@/components/ui/badge";

export type UploadItemStatus = "uploading" | "done" | "failed";

export type UploadItem = {
  id: string;
  file: File;
  status: UploadItemStatus;
  progress: number;
  error?: string;
};

function stageLabel(progress: number): string {
  if (progress >= 100) return "Stored";
  if (progress >= 65) return "Embedding";
  if (progress >= 30) return "Chunking";
  return "Extracting";
}

export function UploadFileRow({ item }: { item: UploadItem }) {
  return (
    <li className="flex flex-col gap-1.5 rounded-card border border-border bg-surface p-3">
      <div className="flex items-center justify-between gap-2">
        <p className="truncate text-[14px] font-medium text-text">
          {item.file.name}
        </p>
        {item.status === "failed" && <Badge variant="danger">Failed</Badge>}
        {item.status === "done" && <Badge variant="ok">Done</Badge>}
      </div>
      {item.status === "failed" ? (
        <p className="text-[13px] text-danger">
          {item.error ?? "Upload failed."}
        </p>
      ) : (
        <>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
            <div
              className="h-full rounded-full bg-accent transition-[width] duration-150 ease-out"
              style={{ width: `${item.progress}%` }}
            />
          </div>
          <p className="text-[13px] text-muted">{stageLabel(item.progress)}</p>
        </>
      )}
    </li>
  );
}
