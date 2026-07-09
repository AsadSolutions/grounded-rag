"use client";

import { useRef, useState, type DragEvent } from "react";

const ACCEPTED_EXTENSIONS = [".pdf", ".txt", ".md"];

function isAcceptedFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export function DropWell({
  onFilesAccepted,
  disabled = false,
}: {
  onFilesAccepted: (files: File[]) => void;
  disabled?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [rejectedNames, setRejectedNames] = useState<string[]>([]);

  function handleFiles(fileList: FileList | null) {
    if (!fileList) return;
    const files = Array.from(fileList);
    const accepted = files.filter(isAcceptedFile);
    const rejected = files.filter((file) => !isAcceptedFile(file));
    setRejectedNames(rejected.map((file) => file.name));
    if (accepted.length > 0) onFilesAccepted(accepted);
  }

  return (
    <div className="flex flex-col gap-2">
      <div
        onDragOver={(e: DragEvent) => {
          e.preventDefault();
          if (!disabled) setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={(e: DragEvent) => {
          e.preventDefault();
          setIsDragOver(false);
          if (disabled) return;
          handleFiles(e.dataTransfer.files);
        }}
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (disabled) return;
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        className={`flex flex-col items-center justify-center gap-2 rounded-card border border-dashed bg-surface-2 px-6 py-12 text-center transition-colors duration-150 ease-out ${
          disabled
            ? "cursor-not-allowed border-border opacity-50"
            : `cursor-pointer ${isDragOver ? "border-accent" : "border-border"}`
        }`}
      >
        <p className="text-[15px] text-text">
          Drag and drop files here, or{" "}
          <span className="text-accent underline underline-offset-4">
            browse
          </span>
        </p>
        <p className="text-[13px] text-muted">PDF, TXT, or MD</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.md"
          disabled={disabled}
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = "";
          }}
          className="hidden"
        />
      </div>
      {rejectedNames.length > 0 && (
        <p className="text-[13px] text-danger">
          {rejectedNames.length === 1
            ? `"${rejectedNames[0]}" isn't supported.`
            : `${rejectedNames.length} files aren't supported (${rejectedNames.join(", ")}).`}{" "}
          Only PDF, TXT, and MD files are accepted.
        </p>
      )}
    </div>
  );
}
