"use client";

import type { ProductCardBlock } from "@/lib/contracts/ecommerce-blocks";

/**
 * Workbench-specific product card.
 *
 * The existing `<ProductCard>` in `components/blocks/` is a faithful
 * renderer of the Python-emitted `ProductCardBlock` shape — it shows
 * the raw `product_id` and is meant for the dev preview surface.
 *
 * The shopper workbench needs a card that:
 *   - puts "Add to compare" as a first-class action
 *   - shows a category-tinted hero band so a row of cards reads at a
 *     glance, even without real product photos
 *   - hides developer-oriented fields (no `product_id` chip)
 *   - shows a "compare-selected" state so it's obvious which cards
 *     are currently in the right-rail tray
 */

const CATEGORY_TONE: Record<
  string,
  { band: string; chip: string; accentText: string; addCta: string; addCtaActive: string }
> = {
  laptop: {
    band: "bg-gradient-to-br from-indigo-500 to-indigo-700",
    chip: "bg-indigo-50 text-indigo-700",
    accentText: "text-indigo-700",
    addCta: "border-indigo-200 text-indigo-700 hover:bg-indigo-50",
    addCtaActive: "border-indigo-700 bg-indigo-700 text-white",
  },
  phone: {
    band: "bg-gradient-to-br from-emerald-500 to-emerald-700",
    chip: "bg-emerald-50 text-emerald-700",
    accentText: "text-emerald-700",
    addCta: "border-emerald-200 text-emerald-700 hover:bg-emerald-50",
    addCtaActive: "border-emerald-700 bg-emerald-700 text-white",
  },
  tablet: {
    band: "bg-gradient-to-br from-amber-500 to-amber-700",
    chip: "bg-amber-50 text-amber-700",
    accentText: "text-amber-700",
    addCta: "border-amber-200 text-amber-700 hover:bg-amber-50",
    addCtaActive: "border-amber-700 bg-amber-700 text-white",
  },
  earbuds: {
    band: "bg-gradient-to-br from-rose-500 to-rose-700",
    chip: "bg-rose-50 text-rose-700",
    accentText: "text-rose-700",
    addCta: "border-rose-200 text-rose-700 hover:bg-rose-50",
    addCtaActive: "border-rose-700 bg-rose-700 text-white",
  },
  monitor: {
    band: "bg-gradient-to-br from-sky-500 to-sky-700",
    chip: "bg-sky-50 text-sky-700",
    accentText: "text-sky-700",
    addCta: "border-sky-200 text-sky-700 hover:bg-sky-50",
    addCtaActive: "border-sky-700 bg-sky-700 text-white",
  },
};

function toneFor(category: string) {
  return CATEGORY_TONE[category] ?? CATEGORY_TONE.laptop;
}

function formatPrice(priceUsd: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(priceUsd);
}

function topSpecs(block: ProductCardBlock): { label: string; value: string }[] {
  // Prefer the two most decision-relevant specs across categories.
  const preferOrder = [
    "Memory",
    "Storage",
    "Display",
    "Screen",
    "Chip",
    "Camera",
    "Battery",
    "Refresh",
    "Weight",
  ];
  const lookup = new Map<string, string>();
  for (const spec of block.specs) lookup.set(spec.label, spec.value);
  const picks: { label: string; value: string }[] = [];
  for (const label of preferOrder) {
    if (picks.length >= 2) break;
    const value = lookup.get(label);
    if (value) picks.push({ label, value });
  }
  if (picks.length < 2) {
    for (const spec of block.specs) {
      if (picks.length >= 2) break;
      if (!picks.find((p) => p.label === spec.label)) {
        picks.push({ label: spec.label, value: spec.value });
      }
    }
  }
  return picks;
}

export function WorkbenchProductCard({
  block,
  selected,
  selectionLimitReached,
  onToggleCompare,
  onAskAdvisor,
}: {
  block: ProductCardBlock;
  selected: boolean;
  selectionLimitReached: boolean;
  onToggleCompare: (productId: string) => void;
  onAskAdvisor: (block: ProductCardBlock) => void;
}) {
  const tone = toneFor(block.category);
  const specs = topSpecs(block);
  const disabledAdd = !selected && selectionLimitReached;
  return (
    <article
      className={[
        "group flex h-full flex-col overflow-hidden rounded-2xl border bg-white shadow-sm transition",
        selected
          ? "border-slate-900 ring-2 ring-slate-900/10"
          : "border-slate-200 hover:border-slate-300 hover:shadow-md",
      ].join(" ")}
    >
      <div className={`relative flex h-20 items-center justify-between px-4 ${tone.band}`}>
        <span className={`rounded-full bg-white/95 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${tone.accentText}`}>
          {block.category}
        </span>
        <span className="rounded-full bg-white/95 px-2.5 py-1 text-xs font-semibold text-slate-900">
          {formatPrice(block.price_usd)}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4">
        <header>
          <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">
            {block.brand}
          </p>
          <h3 className="mt-0.5 text-base font-semibold leading-snug text-slate-950">
            {block.name}
          </h3>
        </header>

        <p className="text-sm leading-6 text-slate-600">{block.summary}</p>

        {specs.length > 0 && (
          <dl className="mt-auto grid grid-cols-2 gap-x-3 gap-y-1.5 border-t border-slate-100 pt-3 text-xs">
            {specs.map((spec) => (
              <div key={spec.label} className="flex flex-col">
                <dt className="text-[11px] text-slate-400">{spec.label}</dt>
                <dd className="font-medium text-slate-800">{spec.value}</dd>
              </div>
            ))}
          </dl>
        )}

        <div className="flex items-center gap-2 pt-1">
          <button
            type="button"
            onClick={() => onToggleCompare(block.product_id)}
            disabled={disabledAdd}
            className={[
              "inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border px-3 py-2 text-xs font-semibold transition",
              "disabled:cursor-not-allowed disabled:opacity-50",
              selected ? tone.addCtaActive : `bg-white ${tone.addCta}`,
            ].join(" ")}
            aria-pressed={selected}
          >
            {selected ? (
              <>
                <svg viewBox="0 0 20 20" fill="currentColor" className="h-3.5 w-3.5">
                  <path
                    fillRule="evenodd"
                    d="M16.704 5.29a1 1 0 0 1 .006 1.414l-7.07 7.13a1 1 0 0 1-1.42.006L3.29 8.92a1 1 0 1 1 1.42-1.41l3.927 3.957 6.36-6.412a1 1 0 0 1 1.414-.006Z"
                    clipRule="evenodd"
                  />
                </svg>
                Selected
              </>
            ) : (
              "Add to compare"
            )}
          </button>
          <button
            type="button"
            onClick={() => onAskAdvisor(block)}
            className="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            title="Ask the advisor about this product"
          >
            Why this?
          </button>
        </div>
      </div>
    </article>
  );
}

export function ProductGrid({
  blocks,
  selectedIds,
  selectionLimit,
  onToggleCompare,
  onAskAdvisor,
  isLoading,
}: {
  blocks: ProductCardBlock[];
  selectedIds: string[];
  selectionLimit: number;
  onToggleCompare: (productId: string) => void;
  onAskAdvisor: (block: ProductCardBlock) => void;
  isLoading: boolean;
}) {
  if (isLoading && blocks.length === 0) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, idx) => (
          <div
            key={idx}
            className="h-72 animate-pulse rounded-2xl border border-slate-200 bg-slate-100/70"
          />
        ))}
      </div>
    );
  }
  if (blocks.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-slate-200 bg-white p-10 text-center">
        <p className="text-base font-semibold text-slate-900">No matches yet</p>
        <p className="max-w-sm text-sm text-slate-500">
          Try widening the budget, switching the category to{" "}
          <span className="font-medium">Any</span>, or picking a different task above.
        </p>
      </div>
    );
  }
  const selectionLimitReached = selectedIds.length >= selectionLimit;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {blocks.map((block) => (
        <WorkbenchProductCard
          key={block.product_id}
          block={block}
          selected={selectedIds.includes(block.product_id)}
          selectionLimitReached={selectionLimitReached}
          onToggleCompare={onToggleCompare}
          onAskAdvisor={onAskAdvisor}
        />
      ))}
    </div>
  );
}
