import type { Metadata } from "next";

import "@fontsource-variable/space-grotesk";
import "@fontsource-variable/inter";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./globals.css";

import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = {
  title: "Reframe — long video in, vertical clips out",
  description:
    "Open-source AI that turns long-form video into speaker-tracked 9:16 Shorts, Reels, and TikToks. Runs locally, stores nothing.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body
        style={
          {
            "--font-display": "'Space Grotesk Variable'",
            "--font-body": "'Inter Variable'",
            "--font-mono": "'IBM Plex Mono'",
          } as React.CSSProperties
        }
      >
        <SiteHeader />
        <main>{children}</main>
        <footer className="border-t border-line py-8">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 font-mono text-xs text-dim sm:px-6">
            <span>Reframe · runs entirely on your machine</span>
            <span>nothing uploaded is ever stored</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
