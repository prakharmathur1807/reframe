"use client";

import { useEffect, useState } from "react";
import { TrendingUp, Loader2, RefreshCw } from "lucide-react";
import { API_URL } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface Trend {
  keyword: string;
  category: string;
  score: number;
  hashtags: string[];
}

export default function TrendsPage() {
  const [trends, setTrends] = useState<Trend[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch_ = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/trends`);
      if (!res.ok) throw new Error(res.statusText);
      const data = (await res.json()) as { trends: Trend[] };
      setTrends(data.trends);
    } catch (e) {
      setError("Could not fetch trends — check the API is running.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void fetch_(); }, []);

  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-dim">Trending Now</p>
          <h1 className="mt-2 font-display text-3xl font-semibold tracking-tight">
            What&apos;s trending today
          </h1>
          <p className="mt-1 text-sm text-dim">
            Google Trends + YouTube · refreshed every 30 minutes
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => void fetch_()} disabled={loading}>
          <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
          Refresh
        </Button>
      </div>

      {loading && (
        <div className="flex min-h-[30vh] items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-rec" />
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-rec/30 bg-rec/5 p-4 text-sm text-rec">{error}</div>
      )}

      {!loading && !error && (
        <div className="grid gap-3 sm:grid-cols-2">
          {trends.map((trend, i) => (
            <TrendCard key={`${trend.keyword}-${i}`} trend={trend} rank={i + 1} />
          ))}
          {trends.length === 0 && (
            <p className="col-span-2 text-center text-dim py-12">
              No trends available right now. Feeds may be temporarily unavailable.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function TrendCard({ trend, rank }: { trend: Trend; rank: number }) {
  const barW = `${trend.score}%`;
  return (
    <div className="rounded-lg border border-line bg-panel p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-rec">{String(rank).padStart(2, "0")}</span>
            <h3 className="font-display text-sm font-semibold truncate">{trend.keyword}</h3>
          </div>
          <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wide text-dim">
            {trend.category}
          </p>
        </div>
        <div className="shrink-0 flex items-center gap-1 text-guide">
          <TrendingUp className="h-3.5 w-3.5" />
          <span className="font-mono text-xs">{trend.score}</span>
        </div>
      </div>
      <div className="mt-3 h-0.5 w-full overflow-hidden rounded-full bg-raised">
        <div className="h-full rounded-full bg-guide/60" style={{ width: barW }} />
      </div>
      <div className="mt-2 flex flex-wrap gap-1">
        {trend.hashtags.slice(0, 3).map((h) => (
          <span key={h} className="font-mono text-[10px] text-dim">{h}</span>
        ))}
      </div>
    </div>
  );
}
