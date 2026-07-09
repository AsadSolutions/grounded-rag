"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function Nav({ tenantId }: { tenantId: string | null }) {
  const pathname = usePathname();

  const staticLinks = [
    { href: "/upload", label: "Upload", active: pathname === "/upload" },
    { href: "/evals", label: "Evals", active: pathname === "/evals" },
  ];

  return (
    <nav className="flex flex-col gap-0.5">
      {tenantId ? (
        <Link
          href={`/chat/${tenantId}`}
          className={`rounded-button px-2 py-1.5 text-[14px] font-medium transition-colors duration-150 ease-out ${
            pathname?.startsWith("/chat")
              ? "bg-accent-soft text-accent"
              : "text-text hover:bg-surface-2"
          }`}
        >
          Chat
        </Link>
      ) : (
        <span className="cursor-not-allowed rounded-button px-2 py-1.5 text-[14px] font-medium text-muted opacity-50">
          Chat
        </span>
      )}
      {staticLinks.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className={`rounded-button px-2 py-1.5 text-[14px] font-medium transition-colors duration-150 ease-out ${
            link.active
              ? "bg-accent-soft text-accent"
              : "text-text hover:bg-surface-2"
          }`}
        >
          {link.label}
        </Link>
      ))}
    </nav>
  );
}
