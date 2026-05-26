"use client";

/**
 * Three-step "decision flow" pill row borrowed from Stitch's stage feel:
 *
 *     Explore  →  Compare  →  Decide
 *
 * Highlights wherever the shopper currently is. The component is purely
 * presentational — the parent passes the current `stage` based on app state
 * (no candidates yet / picks selected / spec table loaded).
 */

export type WorkbenchStage = "explore" | "compare" | "decide";

const STAGES: { id: WorkbenchStage; label: string; hint: string }[] = [
  { id: "explore", label: "Explore", hint: "Pick a task and narrow the shortlist." },
  { id: "compare", label: "Compare", hint: "Hold 2-4 picks side-by-side." },
  { id: "decide", label: "Decide", hint: "Read trade-offs and choose one." },
];

export function StageIndicator({ stage }: { stage: WorkbenchStage }) {
  const activeIdx = STAGES.findIndex((s) => s.id === stage);
  return (
    <ol
      aria-label="Decision flow"
      className="flex w-full flex-wrap items-center gap-2 rounded-xl border border-slate-200 bg-white/80 p-1.5 shadow-sm backdrop-blur-sm"
    >
      {STAGES.map((step, idx) => {
        const isActive = idx === activeIdx;
        const isPast = idx < activeIdx;
        return (
          <li
            key={step.id}
            className="flex flex-1 items-center gap-2 min-w-[140px]"
            aria-current={isActive ? "step" : undefined}
          >
            <div
              className={[
                "flex flex-1 items-center gap-2.5 rounded-lg px-3 py-2 transition",
                isActive
                  ? "bg-slate-950 text-white shadow-sm"
                  : isPast
                    ? "bg-slate-100 text-slate-700"
                    : "text-slate-500",
              ].join(" ")}
            >
              <span
                className={[
                  "flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-mono font-semibold tracking-tight",
                  isActive
                    ? "bg-cyan-300 text-slate-950"
                    : isPast
                      ? "bg-slate-900 text-white"
                      : "bg-slate-200 text-slate-500",
                ].join(" ")}
              >
                {idx + 1}
              </span>
              <div className="flex flex-col">
                <span className="text-[10px] font-mono font-semibold uppercase tracking-[0.18em]">
                  {step.label}
                </span>
                <span
                  className={[
                    "hidden text-[11px] leading-tight md:block",
                    isActive ? "text-cyan-100" : "text-slate-500",
                  ].join(" ")}
                >
                  {step.hint}
                </span>
              </div>
            </div>
            {idx < STAGES.length - 1 && (
              <span
                aria-hidden
                className={[
                  "hidden h-px flex-1 sm:block",
                  isPast ? "bg-slate-300" : "bg-slate-200",
                ].join(" ")}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
