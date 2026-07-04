import Link from "next/link";

const upcoming = [
  { label: "Upload", module: "Module 3" },
  { label: "YouTube", module: "Module 3" },
  { label: "Trending", module: "Module 8" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-ink/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span
            aria-hidden
            className="h-2.5 w-2.5 rounded-full bg-rec animate-rec-blink"
          />
          <span className="font-display text-lg font-semibold tracking-tight">
            Reframe
          </span>
          <span className="hidden font-mono text-[11px] text-dim sm:inline">
            v0.2 · open source
          </span>
        </Link>

        <nav aria-label="Main" className="flex items-center gap-1">
          {upcoming.map((item) => (
            <span
              key={item.label}
              className="hidden items-center gap-1.5 rounded px-3 py-1.5 text-sm text-dim sm:flex"
              title={`Ships in ${item.module}`}
            >
              {item.label}
              <span className="rounded border border-line px-1 py-px font-mono text-[10px] uppercase tracking-wide">
                soon
              </span>
            </span>
          ))}
          <a
            href="#status"
            className="rounded px-3 py-1.5 text-sm text-chalk hover:bg-raised"
          >
            System status
          </a>
        </nav>
      </div>
    </header>
  );
}
