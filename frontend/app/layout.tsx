import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Lora } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";
import { THEME_INIT_SCRIPT } from "@/lib/theme";
import { ToastProvider } from "@/lib/toast-context";
import { ScratchTenantProvider } from "@/lib/scratch-tenant-context";
import { SettingsProvider } from "@/lib/settings-context";

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
      className={`${inter.variable} ${lora.variable} ${jetbrainsMono.variable} h-full scroll-smooth`}
      data-scroll-behavior="smooth"
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col antialiased">
        <div
          suppressHydrationWarning
          className="contents"
          dangerouslySetInnerHTML={{
            __html: `<script id="theme-init">${THEME_INIT_SCRIPT}</script>`,
          }}
        />
        <ThemeProvider>
          <ToastProvider>
            <ScratchTenantProvider>
              <SettingsProvider>{children}</SettingsProvider>
            </ScratchTenantProvider>
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
