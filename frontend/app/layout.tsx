import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Lora } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { MockDataPill } from "@/components/mock-data-pill";
import { THEME_INIT_SCRIPT } from "@/lib/theme";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const lora = Lora({
  variable: "--font-lora",
  subsets: ["latin"],
  weight: ["500", "600"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "GroundedRAG",
  description:
    "Open source multi tenant RAG engine with hybrid retrieval and a self correcting answer loop.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${lora.variable} ${jetbrainsMono.variable} h-full`}
      suppressHydrationWarning
    >
      <head>
        <Script id="theme-init" strategy="beforeInteractive">
          {THEME_INIT_SCRIPT}
        </Script>
      </head>
      <body className="min-h-full flex flex-col antialiased">
        <ThemeProvider>{children}</ThemeProvider>
        <MockDataPill />
      </body>
    </html>
  );
}
