"use client";

import { useState } from "react";
import { Download, ChevronDown, ChevronUp, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { API_URL } from "@/lib/api";

interface ClipMeta {
  youtube_title?: string;
  reel_caption?: string;
  hashtags?: string[];
  seo_keywords?: string[];
  description?: string;
}

interface Clip {
  id: string;
  start: number;
  end: number;
  duration: number;
  viral_score: number;
  title: string;
  hook: string;
  explanation: string;
  wpm: number;
  metadata?: ClipMeta;
}

export function ClipCard({ clip, jobId, index }: { clip: Clip; jobId: string; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const score = clip.viral_score;
  const scoreColor = score >= 75 ? "text-guide" : score >= 50 ? "text-yellow-400" : "text-dim";
  const barColor = score >= 75 ? "bg-guide" : score >= 50 ? "bg-yellow-400" : "bg-dim";

  const fmtTime = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  return (
    <div className="rounded-lg border border-line bg-panel overflow-hidden">
      {/* header */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="font-mono text-xs text-dim">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div>
              <h3 className="font-display text-sm font-semibold text-chalk line-clamp-1">
                {clip.title || `Clip ${index + 1}`}
              </h3>
              <p className="mt-0.5 text-xs text-dim">
                {fmtTime(clip.start)} → {fmtTime(clip.end)} · {clip.duration.toFixed(1)}s · {clip.wpm} WPM
              </p>
            </div>
          </div>

          {/* viral score */}
          <div className="shrink-0 text-center">
            <div className={cn("font-display text-2xl font-bold leading-none", scoreColor)}>
              {score}
            </div>
            <div className="mt-0.5 flex items-center gap-1 font-mono text-[10px] text-dim">
              <Zap className="h-2.5 w-2.5" />
              VIRAL
            </div>
          </div>
        </div>

        {/* score bar */}
        <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-raised">
          <div
            className={cn("h-full rounded-full transition-all", barColor)}
            style={{ width: `${score}%` }}
          />
        </div>

        <p className="mt-2 text-xs text-dim">{clip.explanation}</p>
      </div>

      {/* hook */}
      <div className="border-t border-line px-4 py-2.5 bg-raised/40">
        <p className="text-xs text-dim">
          <span className="font-medium text-chalk">Hook: </span>
          {clip.hook}
        </p>
      </div>

      {/* actions */}
      <div className="flex items-center justify-between gap-2 border-t border-line px-4 py-3">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 text-xs text-dim hover:text-chalk transition-colors"
        >
          {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          {expanded ? "Hide" : "Metadata"}
        </button>
        <a
          href={`${API_URL}/api/clips/${jobId}/${clip.id}/download`}
          download={`reframe_clip_${clip.id}.mp4`}
        >
          <Button size="sm" className="gap-1.5">
            <Download className="h-3.5 w-3.5" />
            Download MP4
          </Button>
        </a>
      </div>

      {/* expanded metadata */}
      {expanded && clip.metadata && (
        <div className="border-t border-line bg-raised/30 px-4 py-4 space-y-3 text-sm">
          {clip.metadata.youtube_title && (
            <MetaRow label="YouTube title" value={clip.metadata.youtube_title} copyable />
          )}
          {clip.metadata.reel_caption && (
            <MetaRow label="Reel caption" value={clip.metadata.reel_caption} multiline copyable />
          )}
          {clip.metadata.hashtags && clip.metadata.hashtags.length > 0 && (
            <div>
              <p className="text-xs text-dim mb-1.5">Hashtags</p>
              <div className="flex flex-wrap gap-1.5">
                {clip.metadata.hashtags.map((h) => (
                  <span key={h} className="rounded border border-line px-2 py-0.5 font-mono text-[11px] text-dim">
                    {h}
                  </span>
                ))}
              </div>
            </div>
          )}
          {clip.metadata.seo_keywords && (
            <MetaRow label="SEO keywords" value={clip.metadata.seo_keywords.join(", ")} />
          )}
        </div>
      )}
    </div>
  );
}

function MetaRow({
  label,
  value,
  multiline,
  copyable,
}: {
  label: string;
  value: string;
  multiline?: boolean;
  copyable?: boolean;
}) {
  const [copied, setCopied] = useState(false);

  const copy = () => {
    void navigator.clipboard.writeText(value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div>
      <div className="flex items-center justify-between gap-2 mb-1">
        <p className="text-xs text-dim">{label}</p>
        {copyable && (
          <button onClick={copy} className="text-[10px] font-mono text-dim hover:text-chalk transition-colors">
            {copied ? "copied!" : "copy"}
          </button>
        )}
      </div>
      {multiline ? (
        <p className="text-xs text-chalk whitespace-pre-wrap">{value}</p>
      ) : (
        <p className="text-xs text-chalk">{value}</p>
      )}
    </div>
  );
}
