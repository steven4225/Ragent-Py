"use client";

import { SpecCompareTable } from "@/components/blocks/spec-compare-table";
import type {
  ProductCardBlock,
  SpecCompareBlock,
} from "@/lib/contracts/ecommerce-blocks";

/**
 * Right-rail compare tray.
 *
 * Decision aid is a first-class citizen here, not a secondary feature
 * hidden below the candidate grid. The tray is always visible: when
 * empty it gently teaches users how to add picks; once two products
 * are selected the primary CTA lights up; once Compare runs the spec
 * table renders inline (no scroll-jumps).
 */

const SELECTION_LIMIT = 4;

function SelectedChip({
  block,
  onRemove,
}: {
  block: ProductCardBlock;
  onRemove: () => void;
}) {
  return (
    <li className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-slate-900">{block.name}</p>
        <p className="text-[11px] text-slate-500">{block.brand}</p>
      </div>
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${block.name} from compare`}
        className="rounded p-1 text-slate-400 transition hover:bg-white hover:text-slate-700"
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

  return (
    <section
      aria-label="Compare selected products"
      className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <div className="flex items-baseline justify-between">
        <div>
          <h2 className="text-sm font-semibold text-slate-950">Decision aid</h2>
          <p className="mt-0.5 text-xs text-slate-500">
            {selectedCount === 0
              ? `Pick up to ${SELECTION_LIMIT} products to compare side-by-side.`
              : selectedCount === 1
                ? "Pick at least one more to compare."
                : `${selectedCount} selected · ready to compare.`}
          </p>
        </div>
        {selectedCount > 0 && (
          <button
            type="button"
            onClick={onClear}
            className="text-xs font-medium text-slate-500 hover:text-slate-900"
          >
            Clear
          </button>
        )}
      </div>

      {selectedCount > 0 ? (
        <ul className="flex flex-col gap-2">
          {selectedBlocks.map((block) => (
            <SelectedChip
              key={block.product_id}
              block={block}
              onRemove={() => onRemove(block.product_id)}
            />
          ))}
        </ul>
      ) : (
        <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-3 py-4 text-center text-xs text-slate-500">
          Tap <span className="font-medium text-slate-900">Add to compare</span> on a
          product card to start.
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={onCompare}
          disabled={!canCompare || isComparing}
          className="inline-flex items-center justify-center rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isComparing ? "Comparing…" : `Compare ${selectedCount > 0 ? `(${selectedCount})` : ""}`}
        </button>
        <button
          type="button"
          onClick={onExplain}
          disabled={!canCompare}
          className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          title="Ask the advisor to explain the trade-offs"
        >
          Explain the trade-offs
        </button>
      </div>

      {compareNotice && (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          {compareNotice}
        </p>
      )}

      {compareBlock && compareBlock.columns.length > 0 && (
        <div className="-mx-1">
          <SpecCompareTable block={compareBlock} />
        </div>
      )}
    </section>
  );
}

export { SELECTION_LIMIT };
