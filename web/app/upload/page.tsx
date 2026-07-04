import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { UploadZone } from "@/components/upload/upload-zone";
import { YoutubeInput } from "@/components/upload/youtube-input";

export const metadata: Metadata = {
  title: "Upload — Reframe",
};

export default function UploadPage() {
  return (
    <div className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <Link
        href="/"
        className="mb-8 inline-flex items-center gap-1.5 font-mono text-xs text-dim hover:text-chalk"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back
      </Link>

      <p className="font-mono text-xs uppercase tracking-[0.2em] text-dim">
        Step 1 of 1
      </p>
      <h1 className="mt-3 font-display text-3xl font-semibold tracking-tight">
        Add your video
      </h1>
      <p className="mt-2 text-dim">
        Your file never leaves this machine — it is processed locally and
        deleted when the job completes.
      </p>

      {/* tabs */}
      <div className="mt-8">
        <Tabs />
      </div>
    </div>
  );
}

function Tabs() {
  // Server component — tab switching handled in the client children.
  // Using a lightweight URL-param-free approach: two sections separated by a
  // visual divider. For Module 3 this is clean enough; a full tab switcher
  // ships in the polish module.
  return (
    <div className="space-y-8">
      <section>
        <SectionLabel icon="📁" label="Upload from device" />
        <div className="mt-4">
          <UploadZone />
        </div>
      </section>

      <div className="flex items-center gap-3">
        <div className="h-px flex-1 bg-line" />
        <span className="font-mono text-xs text-dim">or</span>
        <div className="h-px flex-1 bg-line" />
      </div>

      <section>
        <SectionLabel icon="▶" label="YouTube URL" />
        <p className="mb-4 mt-1 text-sm text-dim">
          Paste a link to a video you own or are authorized to process.
        </p>
        <YoutubeInput />
      </section>
    </div>
  );
}

function SectionLabel({ icon, label }: { icon: string; label: string }) {
  return (
    <div className="flex items-center gap-2">
      <span aria-hidden className="text-base">{icon}</span>
      <h2 className="font-display text-base font-semibold">{label}</h2>
    </div>
  );
}
