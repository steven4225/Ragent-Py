"use client";

import type { ProductCardBlock } from "@/lib/contracts/ecommerce-blocks";

import {
  TIER_LABEL,
  TIER_SUBLINE,
  type RecommendationTier,
  type TieredCandidate,
} from "./recommendation";

/**
 * Workbench-specific product card and the "candidate main stage" grid.
 *
 * The grid is the page's protagonist. Instead of a flat product list it is
 * organised into three recommendation tiers — Best fit / Performance pick /
 * Value pick — borrowed (gestalt only, not look) from Stitch's Decision
 * Matrix. Any remaining candidates fall into a "More candidates" section so
 * the shopper still sees the full shortlist without losing the hierarchy.
 *
 * Each card carries a short MATCH badge and a 1-2 sentence "Why it fits"
 * paragraph that anchors the spec sheet to the active task.
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

const TIER_ACCENT: Record<
  RecommendationTier,
  { ring: string; chip: string; gridSection: string; underline: string }
> = {
  "best-fit": {
    ring: "ring-2 ring-cyan-300/70 border-cyan-300",
    chip: "bg-cyan-100 text-cyan-900 border-cyan-300",
    gridSection: "from-cyan-100/80 via-white to-white",
    underline: "bg-cyan-500",
  },
  performance: {
    ring: "ring-1 ring-indigo-200 border-indigo-200",
    chip: "bg-indigo-50 text-indigo-800 border-indigo-200",
    gridSection: "from-indigo-50 via-white to-white",
    underline: "bg-indigo-500",
  },
  value: {
    ring: "ring-1 ring-emerald-200 border-emerald-200",
    chip: "bg-emerald-50 text-emerald-800 border-emerald-200",
    gridSection: "from-emerald-50 via-white to-white",
    underline: "bg-emerald-500",
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
  candidate,
  selected,
  selectionLimitReached,
  onToggleCompare,
  onAskAdvisor,
}: {
  candidate: TieredCandidate;
  selected: boolean;
  selectionLimitReached: boolean;
  onToggleCompare: (productId: string) => void;
  onAskAdvisor: (block: ProductCardBlock) => void;
}) {
  const { block, tier, whyItFits, matchScore } = candidate;
  const tone = toneFor(block.category);
  const specs = topSpecs(block);
  const disabledAdd = !selected && selectionLimitReached;
  const tierAccent = tier ? TIER_ACCENT[tier] : null;
  return (
    <article
      className={[
        "group relative flex h-full flex-col overflow-hidden rounded-2xl border bg-white shadow-sm transition",
        selected
          ? "border-slate-950 ring-2 ring-slate-950/15"
          : tierAccent
            ? `${tierAccent.ring} hover:shadow-md`
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

      <span
        className="absolute right-3 top-[5.5rem] -translate-y-1/2 rounded-md border border-slate-900/10 bg-slate-950/90 px-2 py-1 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-cyan-200 shadow-sm backdrop-blur"
        aria-label={`Match score ${matchScore} out of 100`}
      >
        {matchScore}/100 match
      </span>

      <div className="flex flex-1 flex-col gap-3 p-4">
        {tier && tierAccent && (
          <span
            className={`inline-flex w-fit items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] ${tierAccent.chip}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${tierAccent.underline}`} />
            {TIER_LABEL[tier]}
          </span>
        )}

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
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1.5 border-t border-slate-100 pt-3 text-xs">
            {specs.map((spec) => (
              <div key={spec.label} className="flex flex-col">
                <dt className="text-[11px] text-slate-400">{spec.label}</dt>
                <dd className="font-medium text-slate-800">{spec.value}</dd>
              </div>
            ))}
          </dl>
        )}

        <div
          className={[
            "mt-auto rounded-xl border p-3",
            tierAccent
              ? "border-slate-200 bg-slate-50"
              : "border-slate-100 bg-slate-50/70",
          ].join(" ")}
        >
          <p className="mb-1 font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-cyan-700">
            Why it fits
          </p>
          <p className="text-[12.5px] leading-snug text-slate-700">{whyItFits}</p>
        </div>

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
                In shortlist
              </>
            ) : (
              "Add to shortlist"
            )}
          </button>
          <button
            type="button"
            onClick={() => onAskAdvisor(block)}
            className="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            title="Ask the decision assistant about this product"
          >
            Why this?
          </button>
        </div>
      </div>
    </article>
  );
}

function TierHeading({
  tier,
  count,
}: {
  tier: RecommendationTier;
  count: number;
}) {
  const accent = TIER_ACCENT[tier];
  return (
    <div className={`mb-3 rounded-xl border border-slate-200 bg-gradient-to-r ${accent.gridSection} px-4 py-3`}>
      <div className="flex items-baseline justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className={`inline-block h-2.5 w-2.5 rounded-full ${accent.underline}`} aria-hidden />
          <h3 className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-950">
            {TIER_LABEL[tier]}
          </h3>
          <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500">
            · {count} {count === 1 ? "card" : "cards"}
          </span>
        </div>
      </div>
      <p className="mt-1 text-[12.5px] leading-snug text-slate-600">
        {TIER_SUBLINE[tier]}
      </p>
    </div>
  );
}

export function ProductGrid({
  candidates,
  selectedIds,
  selectionLimit,
  onToggleCompare,
  onAskAdvisor,
  isLoading,
}: {
  candidates: TieredCandidate[];
  selectedIds: string[];
  selectionLimit: number;
  onToggleCompare: (productId: string) => void;
  onAskAdvisor: (block: ProductCardBlock) => void;
  isLoading: boolean;
}) {
  if (isLoading && candidates.length === 0) {
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
  if (candidates.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-2xl border border-dashed border-slate-200 bg-white p-10 text-center">
        <p className="text-base font-semibold text-slate-900">Nothing in the shortlist yet</p>
        <p className="max-w-sm text-sm text-slate-500">
          Try widening the budget, switching the category to{" "}
          <span className="font-medium">Any</span>, or picking a different task above.
        </p>
      </div>
    );
  }

  const selectionLimitReached = selectedIds.length >= selectionLimit;

  const tiered: Record<RecommendationTier, TieredCandidate[]> = {
    "best-fit": [],
    performance: [],
    value: [],
  };
  const others: TieredCandidate[] = [];
  for (const candidate of candidates) {
    if (candidate.tier) {
      tiered[candidate.tier].push(candidate);
    } else {
      others.push(candidate);
    }
  }

  const renderTier = (tier: RecommendationTier) => {
    const items = tiered[tier];
    if (items.length === 0) return null;
    return (
      <section key={tier} aria-label={TIER_LABEL[tier]}>
        <TierHeading tier={tier} count={items.length} />
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {items.map((candidate) => (
            <WorkbenchProductCard
              key={candidate.block.product_id}
              candidate={candidate}
              selected={selectedIds.includes(candidate.block.product_id)}
              selectionLimitReached={selectionLimitReached}
              onToggleCompare={onToggleCompare}
              onAskAdvisor={onAskAdvisor}
            />
          ))}
        </div>
      </section>
    );
  };

  return (
    <div className="flex flex-col gap-6">
      {renderTier("best-fit")}
      {renderTier("performance")}
      {renderTier("value")}
      {others.length > 0 && (
        <section aria-label="More candidates">
          <div className="mb-3 flex items-baseline gap-3 border-t border-slate-200 pt-4">
            <h3 className="font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-700">
              More candidates
            </h3>
            <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500">
              · {others.length} more in shortlist
            </span>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {others.map((candidate) => (
              <WorkbenchProductCard
                key={candidate.block.product_id}
                candidate={candidate}
                selected={selectedIds.includes(candidate.block.product_id)}
                selectionLimitReached={selectionLimitReached}
                onToggleCompare={onToggleCompare}
                onAskAdvisor={onAskAdvisor}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
