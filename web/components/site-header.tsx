import Link from "next/link";

const NAV = [
  { label: "Upload", href: "/upload" },
  { label: "YouTube", href: "/youtube" },
  { label: "Trending", href: "/trends" },
];

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-ink/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2.5">
          <span aria-hidden className="h-2.5 w-2.5 rounded-full bg-rec animate-rec-blink" />
          <span className="font-display text-lg font-semibold tracking-tight">Reframe</span>
          <span className="hidden font-mono text-[11px] text-dim sm:inline">v1.0 · open source</span>
        </Link>
        <nav aria-label="Main" className="flex items-center gap-1">
          {NAV.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className="rounded px-3 py-1.5 text-sm text-dim hover:bg-raised hover:text-chalk transition-colors"
            >
              {item.label}
            </Link>
          ))}
          <a href="/#status" className="rounded px-3 py-1.5 text-sm text-chalk hover:bg-raised">
            Status
          </a>
        </nav>
      </div>
    </header>
  );
}