"use client";

import { useId } from "react";

import type { ProductCardBlock } from "@/lib/contracts/ecommerce-blocks";

import type { AdvisorState } from "./types";

/**
 * Right-rail decision assistant.
 *
 * Deliberately NOT a chat box and NOT the page's protagonist — it explains
 * the picks the shopper has already made. The structured questions are
 * intentionally narrow:
 *
 *   - "Why is this the best fit?"
 *   - "Explain the trade-offs"
 *   - "What do I lose if I save money?"
 *   - "What's the next best alternative?"
 *
 * Each question is pre-loaded with the current task and the current
 * shortlist, so a single click yields a useful answer instead of a
 * cold-start chat.
 */

function AdvisorIcon({ status }: { status: AdvisorState["status"] }) {
  if (status === "streaming") {
    return (
      <span className="relative inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-950 text-cyan-300">
        <span className="absolute inset-0 animate-ping rounded-full bg-cyan-400/30" />
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="relative h-4 w-4">
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
        </svg>
      </span>
    );
  }
  return (
    <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-950 text-cyan-300">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
        <path d="M12 3v4M12 17v4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M3 12h4M17 12h4M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8" />
      </svg>
    </span>
  );
}

export function AdvisorPanel({
  state,
  selectedBlocks,
  taskSeedQuery,
  onAsk,
  onAskCustom,
  onCancel,
}: {
  state: AdvisorState;
  selectedBlocks: ProductCardBlock[];
  taskSeedQuery: string;
  onAsk: (question: string) => void;
  onAskCustom: (question: string) => void;
  onCancel: () => void;
}) {
  const inputId = useId();
  const selectedCount = selectedBlocks.length;
  const hasSelection = selectedCount >= 1;
  const hasPair = selectedCount >= 2;
  const task = taskSeedQuery.trim() || "the current shopping decision";
  const topPick = selectedBlocks[0];
  const names = selectedBlocks.map((b) => b.name).join(" vs ");

  const quickPrompts: { id: string; label: string; question: string; enabled: boolean; tone: "primary" | "secondary" }[] = [
    {
      id: "fit",
      label: topPick
        ? `Why is "${topPick.name}" the best fit?`
        : "Why is the top pick the best fit?",
      question: topPick
        ? `Given the task "${task}", explain why ${topPick.name} (${topPick.brand}, ${topPick.category}) is the best fit. Be concrete about the specs that matter for this task and reference the price ($${Math.round(topPick.price_usd)}).`
        : "",
      enabled: hasSelection,
      tone: "primary",
    },
    {
      id: "compare",
      label: hasPair
        ? `Explain trade-offs across ${selectedCount} picks`
        : "Explain the trade-offs",
      question: hasPair
        ? `For the task "${task}", compare ${names}. Walk through the key trade-offs and recommend one with a one-line reason.`
        : "",
      enabled: hasPair,
      tone: "secondary",
    },
    {
      id: "save",
      label: "What do I lose if I save money?",
      question: hasSelection
        ? `If I switch from my current shortlist (${names || topPick?.name}) to the cheapest acceptable option for "${task}", what do I give up in real terms? Be concrete (e.g. battery hours, RAM, camera quality).`
        : `For "${task}", what does a shopper give up by picking the cheapest option instead of the best fit? Be concrete.`,
      enabled: true,
      tone: "secondary",
    },
    {
      id: "alt",
      label: "What's the next best alternative?",
      question: hasSelection
        ? `Beyond ${names || topPick?.name}, what's the next best alternative for "${task}"? Suggest one and explain in 2-3 sentences when a shopper would prefer it.`
        : `For "${task}", suggest a strong next-best alternative beyond the obvious top picks and explain when a shopper would prefer it.`,
      enabled: true,
      tone: "secondary",
    },
  ];

  return (
    <section
      aria-label="Decision assistant"
      className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <header className="flex items-start gap-3">
        <AdvisorIcon status={state.status} />
        <div className="flex-1">
          <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.22em] text-cyan-700">
            Decision assistant
          </p>
          <h2 className="text-sm font-semibold text-slate-950">
            Explains the picks. Doesn&apos;t replace your shortlist.
          </h2>
          <p className="mt-0.5 text-[11px] leading-snug text-slate-500">
            Anchored to your active task and your shortlist — answers are one-shot, not a chat thread.
          </p>
        </div>
      </header>

      <div className="grid gap-2 sm:grid-cols-2">
        {quickPrompts.map((prompt) => (
          <button
            key={prompt.id}
            type="button"
            onClick={() => onAsk(prompt.question)}
            disabled={!prompt.enabled || state.status === "streaming"}
            title={prompt.enabled ? prompt.question : "Add at least one pick to enable this."}
            className={[
              "group inline-flex w-full flex-col items-start gap-1 rounded-xl border px-3 py-2.5 text-left text-xs font-medium transition",
              prompt.enabled
                ? prompt.tone === "primary"
                  ? "border-slate-950 bg-slate-950 text-white hover:bg-slate-900"
                  : "border-slate-200 bg-white text-slate-800 hover:border-slate-300 hover:bg-slate-50"
                : "cursor-not-allowed border-slate-100 bg-slate-50 text-slate-300",
            ].join(" ")}
          >
            <span
              className={[
                "font-mono text-[9px] font-semibold uppercase tracking-[0.18em]",
                prompt.enabled
                  ? prompt.tone === "primary"
                    ? "text-cyan-300"
                    : "text-slate-400"
                  : "text-slate-300",
              ].join(" ")}
            >
              Quick question
            </span>
            <span className="line-clamp-2 leading-snug">{prompt.label}</span>
          </button>
        ))}
      </div>

      <form
        className="flex items-center gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          const formData = new FormData(event.currentTarget);
          const value = String(formData.get("q") ?? "").trim();
          if (!value) return;
          onAskCustom(value);
          (event.currentTarget.elements.namedItem("q") as HTMLInputElement | null)?.focus();
          event.currentTarget.reset();
        }}
      >
        <label htmlFor={inputId} className="sr-only">
          Ask the decision assistant a follow-up
        </label>
        <input
          id={inputId}
          name="q"
          type="text"
          autoComplete="off"
          placeholder="Follow up: which one for long flights?"
          disabled={state.status === "streaming"}
          className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-950 focus:outline-none focus:ring-2 focus:ring-cyan-300/60 disabled:cursor-not-allowed disabled:bg-slate-50"
        />
        {state.status === "streaming" ? (
          <button
            type="button"
            onClick={onCancel}
            className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50"
          >
            Stop
          </button>
        ) : (
          <button
            type="submit"
            className="inline-flex items-center rounded-lg bg-slate-950 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-900"
          >
            Ask
          </button>
        )}
      </form>

      {state.error && (
        <p className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
          {state.error}
        </p>
      )}

      {(state.status !== "idle" || state.text.length > 0) && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          {state.question && (
            <p className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-700">
              {state.question.length > 110
                ? `${state.question.slice(0, 110)}…`
                : state.question}
            </p>
          )}
          <p className="whitespace-pre-wrap text-sm leading-7 text-slate-800">
            {state.text || (state.status === "streaming" ? "Reading the shortlist…" : "")}
            {state.status === "streaming" && (
              <span className="ml-1 inline-block h-3 w-1 animate-pulse bg-cyan-500 align-middle" />
            )}
          </p>
          {state.status === "done" && (state.provider || state.model) && (
            <p className="mt-3 font-mono text-[10px] uppercase tracking-wider text-slate-400">
              {state.provider}
              {state.model ? ` · ${state.model}` : ""}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
