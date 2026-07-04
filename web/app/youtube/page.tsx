import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { YoutubeInput } from "@/components/upload/youtube-input";

export const metadata: Metadata = { title: "YouTube URL — Reframe" };

export default function YoutubePage() {
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
        YouTube URL
      </p>
      <h1 className="mt-3 font-display text-3xl font-semibold tracking-tight">
        Process a YouTube video
      </h1>
      <p className="mt-2 text-dim">
        Only submit videos you own or are authorized to download. The file is
        deleted immediately after processing — nothing is stored.
      </p>
      <div className="mt-8">
        <YoutubeInput />
      </div>
    </div>
  );
}
