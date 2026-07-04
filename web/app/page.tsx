import { ApiStatus } from "@/components/api-status";
import { CropStage } from "@/components/crop-stage";
import { PIPELINE_STAGES } from "@/lib/types";

export default function LandingPage() {
  return (
    <>
      {/* Hero */}
      <section className="mx-auto grid max-w-6xl items-center gap-12 px-4 pb-20 pt-16 sm:px-6 lg:grid-cols-[1.05fr_1fr] lg:pt-24">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-dim">
            TC 00:00:00:00 · local-only pipeline
          </p>
          <h1 className="mt-4 font-display text-4xl font-semibold leading-[1.05] tracking-tight sm:text-6xl">
            Long video in.
            <br />
            Vertical clips out.
          </h1>
          <p className="mt-5 max-w-md text-lg text-dim">
            Reframe watches your footage, follows whoever is speaking, and
            cuts speaker-tracked 9:16 clips with karaoke captions and a Viral
            Score — using only open-source models, on your own hardware.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-4">
            <a
              href="#pipeline"
              className="inline-flex h-12 items-center rounded bg-rec px-7 text-base font-medium text-white transition-colors hover:bg-rec/85 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-guide focus-visible:ring-offset-2 focus-visible:ring-offset-ink"
            >
              See how it works
            </a>
            <a
              href="#status"
              className="inline-flex h-12 items-center rounded border border-line bg-panel px-7 text-base text-chalk transition-colors hover:bg-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-guide focus-visible:ring-offset-2 focus-visible:ring-offset-ink"
            >
              Check engine status
            </a>
          </div>
          <p className="mt-4 font-mono text-xs text-dim">
            no accounts · no database · files deleted after every run
          </p>
        </div>
        <CropStage />
      </section>

      {/* Pipeline */}
      <section id="pipeline" className="border-t border-line bg-panel/40">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-dim">
            The pipeline
          </p>
          <h2 className="mt-3 font-display text-2xl font-semibold tracking-tight sm:text-3xl">
            Eleven stages, one pass, zero cloud
          </h2>
          <p className="mt-2 max-w-xl text-dim">
            Every job runs this exact sequence. The processing screen reports
            progress against these same stages, live.
          </p>
          <ol className="mt-10 grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
            {PIPELINE_STAGES.map((stage, index) => (
              <li key={stage.id} className="bg-ink p-5">
                <div className="flex items-baseline justify-between">
                  <span className="font-mono text-xs text-rec">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="font-mono text-[10px] uppercase tracking-wide text-dim">
                    {stage.id}
                  </span>
                </div>
                <h3 className="mt-2 font-display text-base font-medium">
                  {stage.label}
                </h3>
                <p className="mt-1 text-sm text-dim">{stage.detail}</p>
              </li>
            ))}
            <li className="flex items-center justify-center bg-ink p-5">
              <span className="font-mono text-xs text-dim">
                → 1080 × 1920 · H.264 · MP4
              </span>
            </li>
          </ol>
        </div>
      </section>

      {/* Status */}
      <section id="status" className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-dim">
          System status
        </p>
        <h2 className="mb-6 mt-3 font-display text-2xl font-semibold tracking-tight sm:text-3xl">
          Talking to your local engine
        </h2>
        <ApiStatus />
      </section>
    </>
  );
}
