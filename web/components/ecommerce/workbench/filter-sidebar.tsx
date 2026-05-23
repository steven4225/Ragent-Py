"use client";

import { useId } from "react";

import {
  ECOMMERCE_PRODUCT_CATEGORIES,
  type EcommerceProductCategory,
} from "@/lib/contracts/ecommerce-blocks";

import type { FilterState, PriceBand } from "./types";

/**
 * Left sidebar for narrowing the candidate list.
 *
 * Visually modelled after a shopping-site facet panel, NOT a developer
 * control panel: chips for category / price band / brand instead of
 * `<select>` dropdowns + labels, plus a small free-text "Refine"
 * field that augments the current task query.
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
          ? "border-slate-900 bg-slate-900 text-white shadow-sm"
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
      <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
        {title}
      </h3>
      <div className="flex flex-wrap gap-2">{children}</div>
    </div>
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
}: {
  filter: FilterState;
  brands: readonly string[];
  priceBands: readonly PriceBand[];
  onChange: (next: FilterState) => void;
  onClear: () => void;
  visibleCount: number;
  totalCount: number;
}) {
  const refineId = useId();
  return (
    <aside className="flex flex-col gap-5 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-slate-950">Narrow it down</h2>
        <button
          type="button"
          onClick={onClear}
          className="text-xs font-medium text-slate-500 hover:text-slate-900"
        >
          Clear
        </button>
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
          className="mb-2 block text-[11px] font-semibold uppercase tracking-wider text-slate-500"
        >
          Refine
        </label>
        <input
          id={refineId}
          type="text"
          value={filter.refine}
          onChange={(event) => onChange({ ...filter, refine: event.target.value })}
          placeholder="e.g. OLED, 16GB RAM, lightweight"
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/20"
        />
      </div>

      <p className="text-xs text-slate-500">
        Showing <span className="font-semibold text-slate-900">{visibleCount}</span>{" "}
        of {totalCount} matching products.
      </p>
    </aside>
  );
}
