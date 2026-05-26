"use client";

import { useId } from "react";

import {
  ECOMMERCE_PRODUCT_CATEGORIES,
  type EcommerceProductCategory,
} from "@/lib/contracts/ecommerce-blocks";

import type { FilterState, PriceBand } from "./types";

/**
 * Left rail — "Current shortlist" constraints panel.
 *
 * The panel reads top-down as:
 *
 *   1. ACTIVE TASK · the task the shopper picked (or an idle hint).
 *   2. ACTIVE FILTERS · monospace chips for whatever is currently set,
 *      each removable.
 *   3. REFINE · the chip groups (category / budget / brand) and the
 *      free-text refine input — the only place where the shopper still
 *      makes choices.
 *
 * Borrows Stitch's "Active Filters" gestalt but never crosses over into
 * an engineering panel: chips stay readable, labels stay shopper-friendly.
 */

function ChipButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={[
        "inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium transition",
        active
          ? "border-slate-950 bg-slate-950 text-white shadow-sm"
          : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50",
      ].join(" ")}
    >
      {children}
    </button>
  );
}

function FilterGroup({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="border-b border-slate-100 pb-4 last:border-b-0 last:pb-0">
      <h3 className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
        {title}
      </h3>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
  );
}

function ActiveFilterChip({
  label,
  value,
  onRemove,
}: {
  label: string;
  value: string;
  onRemove?: () => void;
}) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-white px-2 py-1 font-mono text-[10px] uppercase tracking-[0.12em] text-slate-700">
      <span className="text-slate-500">{label}:</span>
      <span className="text-slate-900">{value}</span>
      {onRemove && (
        <button
          type="button"
          onClick={onRemove}
          aria-label={`Remove ${label} filter`}
          className="-mr-0.5 rounded p-0.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-900"
        >
          <svg viewBox="0 0 12 12" className="h-2.5 w-2.5" fill="currentColor" aria-hidden>
            <path d="M2.4 1.4 6 5l3.6-3.6 1 1L7 6l3.6 3.6-1 1L6 7l-3.6 3.6-1-1L5 6 1.4 2.4l1-1Z" />
          </svg>
        </button>
      )}
    </span>
  );
}

export function FilterSidebar({
  filter,
  brands,
  priceBands,
  onChange,
  onClear,
  visibleCount,
  totalCount,
  activeTaskTitle,
  activeTaskSubtitle,
}: {
  filter: FilterState;
  brands: readonly string[];
  priceBands: readonly PriceBand[];
  onChange: (next: FilterState) => void;
  onClear: () => void;
  visibleCount: number;
  totalCount: number;
  activeTaskTitle: string | null;
  activeTaskSubtitle: string | null;
}) {
  const refineId = useId();

  const activePriceBand = priceBands.find((b) => b.id === filter.priceBandId);
  const activeChips: { key: string; label: string; value: string; onRemove?: () => void }[] = [];
  if (filter.category) {
    activeChips.push({
      key: "category",
      label: "Category",
      value: filter.category,
      onRemove: () => onChange({ ...filter, category: null }),
    });
  }
  if (activePriceBand && activePriceBand.id !== "any") {
    activeChips.push({
      key: "budget",
      label: "Budget",
      value: activePriceBand.label,
      onRemove: () => onChange({ ...filter, priceBandId: "any" }),
    });
  }
  if (filter.brand) {
    activeChips.push({
      key: "brand",
      label: "Brand",
      value: filter.brand,
      onRemove: () => onChange({ ...filter, brand: null }),
    });
  }
  if (filter.refine.trim()) {
    activeChips.push({
      key: "refine",
      label: "Refine",
      value: filter.refine.trim(),
      onRemove: () => onChange({ ...filter, refine: "" }),
    });
  }

  return (
    <aside className="flex flex-col gap-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-1.5 border-b border-slate-100 pb-4">
        <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.22em] text-cyan-700">
          Active task
        </span>
        {activeTaskTitle ? (
          <>
            <h2 className="text-sm font-semibold leading-snug text-slate-950">
              {activeTaskTitle}
            </h2>
            {activeTaskSubtitle && (
              <p className="text-[11px] leading-snug text-slate-500">
                {activeTaskSubtitle}
              </p>
            )}
          </>
        ) : (
          <p className="text-[12px] leading-snug text-slate-500">
            No task selected — pick a starting point above or use the chips below.
          </p>
        )}
      </div>

      {activeChips.length > 0 && (
        <div>
          <h3 className="mb-2 flex items-center justify-between font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
            <span>Active filters</span>
            <button
              type="button"
              onClick={onClear}
              className="font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-400 hover:text-slate-900"
            >
              Clear all
            </button>
          </h3>
          <div className="flex flex-wrap gap-1.5">
            {activeChips.map((chip) => (
              <ActiveFilterChip
                key={chip.key}
                label={chip.label}
                value={chip.value}
                onRemove={chip.onRemove}
              />
            ))}
          </div>
        </div>
      )}

      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-slate-950">Refine the shortlist</h2>
        {activeChips.length === 0 && (
          <button
            type="button"
            onClick={onClear}
            className="text-xs font-medium text-slate-500 hover:text-slate-900"
          >
            Reset
          </button>
        )}
      </div>

      <FilterGroup title="Category">
        <ChipButton
          active={filter.category === null}
          onClick={() => onChange({ ...filter, category: null })}
        >
          Any
        </ChipButton>
        {ECOMMERCE_PRODUCT_CATEGORIES.map((category) => (
          <ChipButton
            key={category}
            active={filter.category === category}
            onClick={() =>
              onChange({
                ...filter,
                category:
                  filter.category === category
                    ? null
                    : (category as EcommerceProductCategory),
              })
            }
          >
            <span className="capitalize">{category}</span>
          </ChipButton>
        ))}
      </FilterGroup>

      <FilterGroup title="Budget">
        {priceBands.map((band) => (
          <ChipButton
            key={band.id}
            active={filter.priceBandId === band.id}
            onClick={() => onChange({ ...filter, priceBandId: band.id })}
          >
            {band.label}
          </ChipButton>
        ))}
      </FilterGroup>

      <FilterGroup title="Brand">
        <ChipButton
          active={filter.brand === null}
          onClick={() => onChange({ ...filter, brand: null })}
        >
          Any
        </ChipButton>
        {brands.map((brand) => (
          <ChipButton
            key={brand}
            active={filter.brand === brand}
            onClick={() =>
              onChange({
                ...filter,
                brand: filter.brand === brand ? null : brand,
              })
            }
          >
            {brand}
          </ChipButton>
        ))}
      </FilterGroup>

      <div>
        <label
          htmlFor={refineId}
          className="mb-2 block font-mono text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500"
        >
          Refine with words
        </label>
        <input
          id={refineId}
          type="text"
          value={filter.refine}
          onChange={(event) => onChange({ ...filter, refine: event.target.value })}
          placeholder="e.g. OLED, 16GB RAM, lightweight"
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-950 focus:outline-none focus:ring-2 focus:ring-cyan-300/60"
        />
      </div>

      <p className="rounded-lg bg-slate-50 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.16em] text-slate-600">
        Shortlist <span className="text-slate-900 font-semibold">{visibleCount}</span>{" "}
        / matched <span className="text-slate-900 font-semibold">{totalCount}</span>
      </p>
    </aside>
  );
}
