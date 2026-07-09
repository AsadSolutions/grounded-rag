import Image from "next/image";
import Link from "next/link";
import Script from "next/script";
import { Button } from "@/components/ui/button";
import { DemoTenantCard } from "@/components/demo-tenant-card";
import { getDemoTenants } from "@/lib/api";

const STEPS = [
  {
    number: "01",
    title: "Retrieve",
    description:
      "Dense embeddings catch meaning, BM25 catches exact terms, fused with Reciprocal Rank Fusion.",
  },
  {
    number: "02",
    title: "Correct",
    description:
      "A grading node scores every retrieved chunk. A miss triggers a query rewrite and another retrieval pass, capped at two loops.",
  },
  {
    number: "03",
    title: "Verify",
    description:
      "Every claim is checked against its cited sources before you see it. An ungrounded answer regenerates once, then ships with a low confidence flag.",
  },
] as const;

export default async function Home() {
  const demoTenants = await getDemoTenants();

  return (
    <div className="flex flex-1 flex-col">
      <section className="flex flex-col items-center gap-8 px-6 pb-20 pt-24 text-center">
        <div>
          <Image
            src="/logo.svg"
            width={380}
            height={279}
            alt="GroundedRAG — Answers you can verify."
            className="dark:hidden"
            priority
          />
          <Image
            src="/logo-dark.svg"
            width={380}
            height={279}
            alt="GroundedRAG — Answers you can verify."
            className="hidden dark:block"
            priority
          />
        </div>
        <p className="max-w-xl text-[15px] leading-[1.6] text-muted">
          GroundedRAG answers questions from your documents and shows its
          work. Every answer is checked against the sources before you see
          it, graded, verified, and cited, or honestly flagged when the
          documents don&apos;t contain the answer.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <Button id="try-demo-button" href="#demo" variant="primary">
            Try a demo
          </Button>
          <Button href="/upload" variant="ghost">
            Upload your own documents
          </Button>
        </div>
      </section>

      <section
        id="demo"
        className="mx-auto flex w-full max-w-content flex-col gap-6 px-6 py-16"
      >
        <p className="text-[11px] font-medium uppercase tracking-[0.08em] text-muted">
          Try it on real documents
        </p>
        <div className="grid gap-4 sm:grid-cols-2">
          {demoTenants.map((tenant) => (
            <DemoTenantCard key={tenant.id} tenant={tenant} />
          ))}
        </div>
      </section>

      <section className="mx-auto flex w-full max-w-content flex-col gap-8 px-6 py-16">
        <div className="grid gap-8 sm:grid-cols-3">
          {STEPS.map((step) => (
            <div key={step.number} className="flex flex-col gap-2">
              <span className="font-serif text-[28px] text-accent">
                {step.number}
              </span>
              <h3 className="font-serif text-[20px] text-text">{step.title}</h3>
              <p className="text-[15px] leading-[1.6] text-muted">
                {step.description}
              </p>
            </div>
          ))}
        </div>
        <Link
          href="/evals"
          className="text-[13px] text-muted underline decoration-border underline-offset-4 transition-colors duration-150 ease-out hover:text-accent"
        >
          See the measured results
        </Link>
      </section>

      <footer className="mt-auto flex flex-col items-center gap-3 border-t border-border px-6 py-8 text-[13px] text-muted sm:flex-row sm:justify-between">
        <a
          href="https://github.com/AsadSolutions/grounded-rag"
          className="flex items-center gap-2 transition-colors duration-150 ease-out hover:text-accent"
        >
          <Image src="/icon.svg" width={20} height={20} alt="" />
          Open source · MIT
        </a>
        <a
          href="https://asadsaeed.info"
          className="transition-colors duration-150 ease-out hover:text-accent"
        >
          Built by Asad Saeed
        </a>
      </footer>

      {/* Smooth-scrolls to the demo section on click without touching the
          URL — intercepts and preventDefault()s the anchor's default hash
          navigation, same imperative-script pattern as theme-init above. */}
      <Script id="demo-scroll" strategy="afterInteractive">
        {`
          document.addEventListener("click", function (e) {
            var trigger = e.target.closest("#try-demo-button");
            if (!trigger) return;
            e.preventDefault();
            document.getElementById("demo")?.scrollIntoView({ behavior: "smooth" });
          });
        `}
      </Script>
    </div>
  );
}
