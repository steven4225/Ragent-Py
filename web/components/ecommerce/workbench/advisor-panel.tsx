"use client";

import { useId } from "react";

import type { ProductCardBlock } from "@/lib/contracts/ecommerce-blocks";

import type { AdvisorState } from "./types";

/**
 * Right-rail AI advisor panel.
 *
 * Deliberately NOT a chat box — it's a "Why?" / "Compare these" /
 * "Which one for me?" guidance surface. The big input is replaced by
 * structured prompts that hand the advisor enough context (selected
 * product ids, current task seed) to answer in one shot.
 */

function AdvisorIcon({ status }: { status: AdvisorState["status"] }) {
  if (status === "streaming") {
    return (
      <span className="relative inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-white">
        <span className="absolute inset-0 animate-ping rounded-full bg-slate-900/40" />
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="relative h-4 w-4">
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
        </svg>
      </span>
    );
  }
  return (
    <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-white">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4">
        <path d="M12 2 14.39 7.42 20 8.27l-4 3.9.95 5.53L12 15.1 7.05 17.7 8 12.17l-4-3.9 5.61-.85L12 2z" />
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

  const quickPrompts: { id: string; label: string; question: string; enabled: boolean }[] = [
    {
      id: "fit",
      label: hasSelection
        ? `Why does "${selectedBlocks[0]?.name}" fit my task?`
        : "Why does my top pick fit?",
      question: hasSelection
        ? `Given the task "${taskSeedQuery || "shopping for a 3C product"}", explain why ${selectedBlocks
            .map((block) => block.name)
            .join(" and ")} is a strong fit. Be concrete about specs that matter.`
        : "",
      enabled: hasSelection,
    },
    {
      id: "compare",
      label: hasPair
        ? `Trade-offs between ${selectedBlocks.length} picks`
        : "Trade-offs between picks",
      question: hasPair
        ? `Compare ${selectedBlocks
            .map((block) => block.name)
            .join(" vs ")} for the task "${taskSeedQuery || "general shopping"}". Highlight key trade-offs and a recommended winner.`
        : "",
      enabled: hasPair,
    },
    {
      id: "decide",
      label: "Help me decide",
      question:
        selectedCount > 0
          ? `I'm choosing between ${selectedBlocks
              .map((block) => block.name)
              .join(", ")}. My task is "${taskSeedQuery || "shopping for a 3C product"}". Walk me through the decision and recommend one.`
          : `Recommend the best product for "${taskSeedQuery || "shopping for a 3C product"}" and explain why.`,
      enabled: true,
    },
  ];

  return (
    <section
      aria-label="AI shopping advisor"
      className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <header className="flex items-center gap-3">
        <AdvisorIcon status={state.status} />
        <div className="flex-1">
          <h2 className="text-sm font-semibold text-slate-950">Shopping advisor</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            Explains the picks. Doesn&apos;t shop for you.
          </p>
        </div>
      </header>

      <div className="flex flex-wrap gap-2">
        {quickPrompts.map((prompt) => (
          <button
            key={prompt.id}
            type="button"
            onClick={() => onAsk(prompt.question)}
            disabled={!prompt.enabled || state.status === "streaming"}
            className={[
              "inline-flex max-w-full items-center rounded-full border px-3 py-1.5 text-xs font-medium transition",
              prompt.enabled
                ? "border-slate-200 bg-white text-slate-700 hover:border-slate-900 hover:bg-slate-900 hover:text-white"
                : "cursor-not-allowed border-slate-100 bg-slate-50 text-slate-300",
            ].join(" ")}
            title={prompt.enabled ? prompt.question : "Pick a product first."}
          >
            <span className="max-w-[220px] truncate">{prompt.label}</span>
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
          Ask the advisor a custom question
        </label>
        <input
          id={inputId}
          name="q"
          type="text"
          autoComplete="off"
          placeholder="Or ask: which one for long flights?"
          disabled={state.status === "streaming"}
          className="flex-1 rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/20 disabled:cursor-not-allowed disabled:bg-slate-50"
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
            className="inline-flex items-center rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white hover:bg-slate-800"
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
        <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
          {state.question && (
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
              {state.question.length > 110
                ? `${state.question.slice(0, 110)}…`
                : state.question}
            </p>
          )}
          <p className="whitespace-pre-wrap text-sm leading-7 text-slate-800">
            {state.text || (state.status === "streaming" ? "Thinking…" : "")}
            {state.status === "streaming" && (
              <span className="ml-1 inline-block h-3 w-1 animate-pulse bg-slate-400 align-middle" />
            )}
          </p>
          {state.status === "done" && (state.provider || state.model) && (
            <p className="mt-3 text-[10px] uppercase tracking-wider text-slate-400">
              {state.provider}
              {state.model ? ` · ${state.model}` : ""}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
