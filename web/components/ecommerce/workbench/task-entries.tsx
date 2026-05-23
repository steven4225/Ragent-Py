"use client";

import type { TaskEntry } from "./types";

/**
 * Hero strip of predefined shopping starting-points.
 *
 * Lives at the top of the workbench so a first-time visitor sees
 * concrete tasks (e.g. "work laptop under $1500") instead of an empty
 * input. Selecting an entry seeds the filter + advisor query.
 */

const TONE_TO_CLASSES: Record<
  TaskEntry["tone"],
  { card: string; accent: string; icon: string }
> = {
  indigo: {
    card: "border-indigo-100 hover:border-indigo-300",
    accent: "bg-gradient-to-br from-indigo-500/10 to-indigo-500/0 text-indigo-700",
    icon: "bg-indigo-500 text-white",
  },
  emerald: {
    card: "border-emerald-100 hover:border-emerald-300",
    accent: "bg-gradient-to-br from-emerald-500/10 to-emerald-500/0 text-emerald-700",
    icon: "bg-emerald-500 text-white",
  },
  amber: {
    card: "border-amber-100 hover:border-amber-300",
    accent: "bg-gradient-to-br from-amber-500/10 to-amber-500/0 text-amber-700",
    icon: "bg-amber-500 text-white",
  },
  rose: {
    card: "border-rose-100 hover:border-rose-300",
    accent: "bg-gradient-to-br from-rose-500/10 to-rose-500/0 text-rose-700",
    icon: "bg-rose-500 text-white",
  },
  sky: {
    card: "border-sky-100 hover:border-sky-300",
    accent: "bg-gradient-to-br from-sky-500/10 to-sky-500/0 text-sky-700",
    icon: "bg-sky-500 text-white",
  },
  violet: {
    card: "border-violet-100 hover:border-violet-300",
    accent: "bg-gradient-to-br from-violet-500/10 to-violet-500/0 text-violet-700",
    icon: "bg-violet-500 text-white",
  },
};

function CategoryGlyph({ category }: { category: TaskEntry["category"] }) {
  // Light-weight inline SVGs keep us network-free and don't depend on
  // the product image assets that don't ship in this preview.
  if (category === "laptop") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
        <rect x="3" y="5" width="18" height="11" rx="1.5" />
        <path d="M2 19h20" />
      </svg>
    );
  }
  if (category === "phone") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
        <rect x="6" y="2" width="12" height="20" rx="2.5" />
        <path d="M11 18h2" />
      </svg>
    );
  }
  if (category === "tablet") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
        <rect x="4" y="3" width="16" height="18" rx="2" />
        <path d="M10 18h4" />
      </svg>
    );
  }
  if (category === "earbuds") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
        <path d="M7 4c-2 1-3 4-3 7 0 3 1.5 5 3 5 1 0 1.5-1 1.5-2.5V11a3 3 0 0 0-3-3" />
        <path d="M17 4c2 1 3 4 3 7 0 3-1.5 5-3 5-1 0-1.5-1-1.5-2.5V11a3 3 0 0 1 3-3" />
      </svg>
    );
  }
  if (category === "monitor") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
        <rect x="2" y="4" width="20" height="13" rx="1.5" />
        <path d="M8 21h8M12 17v4" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5">
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}

export function TaskEntries({
  entries,
  activeEntryId,
  onPick,
}: {
  entries: readonly TaskEntry[];
  activeEntryId: string | null;
  onPick: (entry: TaskEntry) => void;
}) {
  return (
    <section aria-label="Pick a shopping task">
      <div className="mb-3 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
          Start with a task
        </h2>
        <span className="text-xs text-slate-400">
          Pick one to seed the filters and the advisor.
        </span>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {entries.map((entry) => {
          const tone = TONE_TO_CLASSES[entry.tone];
          const isActive = entry.id === activeEntryId;
          return (
            <button
              key={entry.id}
              type="button"
              onClick={() => onPick(entry)}
              aria-pressed={isActive}
              className={[
                "group relative flex h-full flex-col items-start gap-2 overflow-hidden rounded-2xl border bg-white p-4 text-left shadow-sm transition",
                "hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-900/30",
                tone.card,
                isActive ? "ring-2 ring-slate-900" : "",
              ].join(" ")}
            >
              <div className={`absolute inset-0 ${tone.accent}`} aria-hidden />
              <span className={`relative z-[1] inline-flex h-9 w-9 items-center justify-center rounded-xl ${tone.icon}`}>
                <CategoryGlyph category={entry.category} />
              </span>
              <h3 className="relative z-[1] text-sm font-semibold leading-tight text-slate-950">
                {entry.title}
              </h3>
              <p className="relative z-[1] text-xs leading-snug text-slate-600">
                {entry.subtitle}
              </p>
            </button>
          );
        })}
      </div>
    </section>
  );
}
