"use client";

import { useEffect, useMemo, useState, useTransition } from "react";

import { ProductCard } from "@/components/blocks/product-card";
import {
  ECOMMERCE_PRODUCT_CATEGORIES,
  type EcommerceProductCategory,
  type EcommerceSearchResponse,
  type ProductCardBlock,
} from "@/lib/contracts/ecommerce-blocks";

/**
 * Preview page for the ecommerce module's `ProductCardBlock`.
 *
 * This page is intentionally separate from the main chat shell:
 * Step D ships the block end-to-end without modifying
 * `services/chat_service`. The chat integration arrives once the
 * GenerationAdapter is wired with a real LLM provider.
 */

const PRICE_BANDS: { label: string; min?: number; max?: number }[] = [
  { label: "Any price" },
  { label: "Under $500", max: 500 },
  { label: "$500 – $1000", min: 500, max: 1000 },
  { label: "$1000 – $1500", min: 1000, max: 1500 },
  { label: "$1500+", min: 1500 },
];

const CATEGORY_OPTIONS: ("all" | EcommerceProductCategory)[] = [
  "all",
  ...ECOMMERCE_PRODUCT_CATEGORIES,
];

interface PreviewState {
  total: number;
  blocks: ProductCardBlock[];
  query: string;
  loadedAt: number;
}

const INITIAL_STATE: PreviewState = {
  total: 0,
  blocks: [],
  query: "",
  loadedAt: 0,
};

async function fetchPreview(payload: {
  query: string;
  category: string | null;
  minPrice?: number;
  maxPrice?: number;
}): Promise<EcommerceSearchResponse> {
  const response = await fetch("/api/preview/ecommerce/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: payload.query,
      filters: {
        category: payload.category ?? null,
        min_price_usd: payload.minPrice ?? null,
        max_price_usd: payload.maxPrice ?? null,
      },
      limit: 12,
    }),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Preview request failed (${response.status}): ${text}`);
  }
  return (await response.json()) as EcommerceSearchResponse;
}

export default function EcommercePreviewPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<"all" | EcommerceProductCategory>("all");
  const [priceBandLabel, setPriceBandLabel] = useState<string>(PRICE_BANDS[0].label);
  const [state, setState] = useState<PreviewState>(INITIAL_STATE);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const activePriceBand = useMemo(
    () => PRICE_BANDS.find((band) => band.label === priceBandLabel) ?? PRICE_BANDS[0],
    [priceBandLabel],
  );

  function runSearch(currentQuery: string) {
    setError(null);
    startTransition(async () => {
      try {
        const result = await fetchPreview({
          query: currentQuery,
          category: category === "all" ? null : category,
          minPrice: activePriceBand.min,
          maxPrice: activePriceBand.max,
        });
        setState({
          total: result.total,
          blocks: result.blocks,
          query: result.query,
          loadedAt: Date.now(),
        });
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Unknown error.");
      }
    });
  }

  useEffect(() => {
    runSearch("");
    // run once on mount so the page loads with the recent-catalog view
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-10">
      <header className="flex flex-col gap-2">
        <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">
          Module preview
        </p>
        <h1 className="text-2xl font-semibold text-slate-950">
          Ecommerce module · ProductCardBlock
        </h1>
        <p className="max-w-3xl text-sm leading-6 text-slate-600">
          Type-safe `product_card` blocks emitted by the Python-side
          ecommerce module against a static 3C fixture. The blocks land
          here without touching the chat pipeline — chat integration is
          deferred to the next push, after the generation adapter is
          wired with a real LLM provider.
        </p>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <form
          className="grid gap-3 sm:grid-cols-[1fr_auto_auto_auto]"
          onSubmit={(event) => {
            event.preventDefault();
            runSearch(query);
          }}
        >
          <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
            Query
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder='e.g. "MacBook", "OLED phone", or "monitor"'
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/30"
            />
          </label>

          <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
            Category
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value as "all" | EcommerceProductCategory)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/30"
            >
              {CATEGORY_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option === "all" ? "Any category" : option}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1 text-xs font-medium text-slate-500">
            Price band
            <select
              value={priceBandLabel}
              onChange={(event) => setPriceBandLabel(event.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-teal-500 focus:outline-none focus:ring-2 focus:ring-teal-500/30"
            >
              {PRICE_BANDS.map((band) => (
                <option key={band.label} value={band.label}>
                  {band.label}
                </option>
              ))}
            </select>
          </label>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={isPending}
              className="inline-flex h-[38px] items-center justify-center rounded-lg bg-teal-600 px-4 text-sm font-medium text-white shadow-sm transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isPending ? "Searching..." : "Search"}
            </button>
          </div>
        </form>
      </section>

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      )}

      <section className="flex items-center justify-between">
        <p className="text-xs text-slate-500">
          {isPending
            ? "Loading..."
            : `${state.total} block${state.total === 1 ? "" : "s"} from python-ecommerce-catalog · query: ${state.query ? `"${state.query}"` : "(all)"}`}
        </p>
        <p className="text-[11px] text-slate-400">
          source: <code className="font-mono">/internal/ecommerce/search</code>
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {state.blocks.map((block) => (
          <ProductCard key={block.product_id} block={block} />
        ))}
      </section>

      {state.blocks.length === 0 && !isPending && !error && (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-sm text-slate-500">
          No products match the current filters.
        </div>
      )}
    </main>
  );
}
