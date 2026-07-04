/**
 * The signature element: a 16:9 frame with a 9:16 crop window that slowly
 * tracks between two speakers, the way the real pipeline's virtual camera
 * will. Pure CSS animation; honors prefers-reduced-motion via globals.css.
 */
export function CropStage() {
  return (
    <figure aria-label="Diagram of a 9:16 crop window tracking a speaker inside a 16:9 frame">
      <div className="relative aspect-video w-full overflow-hidden rounded-lg border border-line bg-panel">
        {/* rule-of-thirds guides */}
        <div aria-hidden className="absolute inset-0">
          <div className="absolute left-1/3 top-0 h-full w-px bg-line/60" />
          <div className="absolute left-2/3 top-0 h-full w-px bg-line/60" />
          <div className="absolute left-0 top-1/3 h-px w-full bg-line/60" />
          <div className="absolute left-0 top-2/3 h-px w-full bg-line/60" />
        </div>

        {/* two speakers */}
        <div aria-hidden className="absolute inset-0">
          <Speaker className="left-[16%] top-[34%]" />
          <Speaker className="left-[66%] top-[38%]" muted />
        </div>

        {/* the 9:16 crop window — width chosen so height fits: 9/16 of frame height */}
        <div
          aria-hidden
          className="absolute left-[7%] top-[4%] h-[92%] animate-crop-track"
          style={{ aspectRatio: "9 / 16" }}
        >
          <div className="absolute inset-0 rounded border-2 border-rec shadow-[0_0_0_9999px_hsl(var(--ink)/0.55)]" />
          {/* safe-area guide inside the crop */}
          <div className="absolute inset-[9%] rounded-sm border border-dashed border-guide/70" />
          <span className="absolute -top-0.5 left-2 -translate-y-full rounded-t bg-rec px-1.5 py-0.5 font-mono text-[10px] font-medium text-white">
            9:16
          </span>
        </div>

        {/* timecode strip */}
        <div
          aria-hidden
          className="absolute bottom-2 left-2 rounded bg-ink/80 px-2 py-1 font-mono text-[11px] text-dim"
        >
          TC 00:00:12:04
        </div>
        <div
          aria-hidden
          className="absolute bottom-2 right-2 flex items-center gap-1.5 rounded bg-ink/80 px-2 py-1 font-mono text-[11px] text-rec"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-rec animate-rec-blink" />
          REC
        </div>
      </div>
      <figcaption className="mt-3 text-sm text-dim">
        The virtual camera follows the active speaker — no keyframing, no
        cropped heads.
      </figcaption>
    </figure>
  );
}

function Speaker({ className, muted }: { className: string; muted?: boolean }) {
  return (
    <div className={`absolute ${className}`}>
      <div
        className={`h-10 w-10 rounded-full sm:h-12 sm:w-12 ${
          muted ? "bg-raised" : "bg-guide/80"
        }`}
      />
      <div
        className={`mx-auto mt-1 h-8 w-14 rounded-t-lg sm:h-10 sm:w-16 ${
          muted ? "bg-raised" : "bg-guide/50"
        }`}
      />
    </div>
  );
}
