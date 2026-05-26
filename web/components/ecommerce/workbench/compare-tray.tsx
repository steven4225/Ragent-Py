"use client";

import { SpecCompareTable } from "@/components/blocks/spec-compare-table";
import type {
  ProductCardBlock,
  SpecCompareBlock,
} from "@/lib/contracts/ecommerce-blocks";

/**
 * Right-rail decision core.
 *
 * The compare tray is no longer a "side feature" — it carries the strongest
 * decision atmosphere on the page:
 *
 *   - SHORTLIST · a large numeral (2/4) tells the shopper exactly where
 *     they are on the way to a comparison.
 *   - The Compare CTA is full-width and lights up the moment a viable
 *     pair is in the shortlist.
 *   - When the spec table arrives, a small DECISION SUMMARY anchor
 *     introduces it instead of dropping it in unannounced.
 */

const SELECTION_LIMIT = 4;

function SelectedRow({
  block,
  index,
  onRemove,
}: {
  block: ProductCardBlock;
  index: number;
  onRemove: () => void;
}) {
  return (
    <li className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-[inset_0_0_0_1px_rgba(15,23,42,0.02)]">
      <div className="flex min-w-0 items-center gap-2.5">
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-md bg-slate-950 font-mono text-[10px] font-semibold text-cyan-300">
          {index + 1}
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-slate-900">{block.name}</p>
          <p className="text-[11px] text-slate-500">{block.brand}</p>
        </div>
      </div>
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${block.name} from the shortlist`}
        className="rounded p-1 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
      >
        <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
          <path
            fillRule="evenodd"
            d="M4.293 4.293a1 1 0 0 1 1.414 0L10 8.586l4.293-4.293a1 1 0 1 1 1.414 1.414L11.414 10l4.293 4.293a1 1 0 0 1-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 0 1-1.414-1.414L8.586 10 4.293 5.707a1 1 0 0 1 0-1.414Z"
            clipRule="evenodd"
          />
        </svg>
      </button>
    </li>
  );
}

export function CompareTray({
  selectedBlocks,
  compareBlock,
  isComparing,
  compareNotice,
  onRemove,
  onClear,
  onCompare,
  onExplain,
}: {
  selectedBlocks: ProductCardBlock[];
  compareBlock: SpecCompareBlock | null;
  isComparing: boolean;
  compareNotice: string | null;
  onRemove: (productId: string) => void;
  onClear: () => void;
  onCompare: () => void;
  onExplain: () => void;
}) {
  const selectedCount = selectedBlocks.length;
  const canCompare = selectedCount >= 2;

  const fillerSlots = Math.max(0, 2 - selectedCount);

  return (
    <section
      aria-label="Decision core"
      className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-gradient-to-b from-white via-white to-cyan-50/30 p-5 shadow-sm"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.22em] text-cyan-700">
            Decision core
          </p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="font-mono text-3xl font-semibold leading-none text-slate-950">
              {selectedCount}
            </span>
            <span className="font-mono text-xs uppercase tracking-[0.16em] text-slate-500">
              / {SELECTION_LIMIT} in shortlist
            </span>
          </div>
          <p className="mt-1 text-[12.5px] leading-snug text-slate-600">
            {selectedCount === 0
              ? "Add cards from the main stage to begin a side-by-side comparison."
              : selectedCount === 1
                ? "Add at least one more pick to unlock the side-by-side spec table."
                : "Ready — open the spec table to read trade-offs and decide."}
          </p>
        </div>
        {selectedCount > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 hover:text-slate-900"
          >
            Clear all
          </button>
        )}
      </div>

      <ul className="flex flex-col gap-2">
        {selectedBlocks.map((block, idx) => (
          <SelectedRow
            key={block.product_id}
            block={block}
            index={idx}
            onRemove={() => onRemove(block.product_id)}
          />
        ))}
        {Array.from({ length: fillerSlots }).map((_, idx) => (
          <li
            key={`filler-${idx}`}
            className="flex items-center gap-2.5 rounded-lg border border-dashed border-slate-200 bg-slate-50/60 px-3 py-2"
          >
            <span className="inline-flex h-5 w-5 items-center justify-center rounded-md border border-dashed border-slate-300 bg-white font-mono text-[10px] font-semibold text-slate-400">
              {selectedCount + idx + 1}
            </span>
            <p className="text-[12px] text-slate-400">Open spot — add another candidate</p>
          </li>
        ))}
      </ul>

      <button
        type="button"
        onClick={onCompare}
        disabled={!canCompare || isComparing}
        className={[
          "inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold shadow-sm transition",
          canCompare
            ? "bg-slate-950 text-white hover:bg-slate-900"
            : "cursor-not-allowed bg-slate-200 text-slate-400",
        ].join(" ")}
      >
        {isComparing ? (
          <>
            <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" opacity="0.25" />
              <path d="M21 12a9 9 0 0 1-9 9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
            </svg>
            Building spec table…
          </>
        ) : canCompare ? (
          <>
            Compare {selectedCount} picks side-by-side
            <span className="font-mono text-[10px] tracking-[0.18em] text-cyan-300">
              ENTER
            </span>
          </>
        ) : (
          "Add at least 2 picks to compare"
        )}
      </button>

      <button
        type="button"
        onClick={onExplain}
        disabled={!canCompare}
        className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
        title="Ask the decision assistant to explain the trade-offs"
      >
        Explain the trade-offs in words
      </button>

      {compareNotice && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          {compareNotice}
        </p>
      )}

      {compareBlock && compareBlock.columns.length > 0 && (
        <div className="-mx-1 mt-1">
          <div className="mb-2 flex items-center gap-2 px-1">
            <span className="h-2 w-2 rounded-full bg-cyan-500" aria-hidden />
            <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-700">
              Decision summary · spec table
            </span>
          </div>
          <SpecCompareTable block={compareBlock} />
        </div>
      )}
    </section>
  );
}

export { SELECTION_LIMIT };
