"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AdvisorPanel } from "@/components/ecommerce/workbench/advisor-panel";
import {
  CompareTray,
  SELECTION_LIMIT,
} from "@/components/ecommerce/workbench/compare-tray";
import { FilterSidebar } from "@/components/ecommerce/workbench/filter-sidebar";
import { ProductGrid } from "@/components/ecommerce/workbench/product-grid";
import { TaskEntries } from "@/components/ecommerce/workbench/task-entries";
import type {
  AdvisorState,
  FilterState,
  PriceBand,
  TaskEntry,
} from "@/components/ecommerce/workbench/types";
import type {
  EcommerceChatStreamEvent,
  EcommerceCompareResponse,
  EcommerceProductCategory,
  EcommerceSearchResponse,
  ProductCardBlock,
  SpecCompareBlock,
} from "@/lib/contracts/ecommerce-blocks";

/**
 * Shopper workbench (v2 preview).
 *
 * The old `/preview/ecommerce` page is a faithful dev preview of the
 * Python-side ecommerce module — it shows raw block ids, exposes the
 * internal endpoint names, and treats the search bar as the page's
 * starting point. That reads as "a chat system with shopping bits
 * bolted on".
 *
 * This page is a deliberate redesign of just the front-end: the same
 * `/api/preview/ecommerce/*` endpoints, the same `SpecCompareTable`
 * primitive, but the information architecture is shopper-first:
 *
 *   1. Hero strip of concrete shopping tasks (no empty input).
 *   2. Left rail = facet filters (chips, not <select>s).
 *   3. Center = candidate product grid (always visible).
 *   4. Right rail (top) = compare tray (decision aid is a first-class
 *      action; spec table renders inline once Compare runs).
 *   5. Right rail (bottom) = AI advisor (explains the picks, doesn't
 *      try to be the page's center of gravity).
 *
 * Does NOT touch `services/chat_service`, the main `/api/chat`
 * pipeline, the main chat UI, or any backend code. Reuses
 * `ProductCardBlock` / `SpecCompareBlock` shapes and existing
 * `SpecCompareTable` primitive.
 */

const PRICE_BANDS: readonly PriceBand[] = [
  { id: "any", label: "Any" },
  { id: "lt500", label: "< $500", max: 500 },
  { id: "500-1000", label: "$500–1000", min: 500, max: 1000 },
  { id: "1000-1500", label: "$1000–1500", min: 1000, max: 1500 },
  { id: "1500-plus", label: "$1500+", min: 1500 },
];

const TASK_ENTRIES: readonly TaskEntry[] = [
  {
    id: "work-laptop",
    title: "Work laptop under $1500",
    subtitle: "Reliable everyday machine for code and calls.",
    category: "laptop",
    maxPrice: 1500,
    query: "work laptop under $1500 with at least 16GB RAM and good battery",
    tone: "indigo",
  },
  {
    id: "premium-phone",
    title: "Premium phone",
    subtitle: "Top-tier camera and display for daily use.",
    category: "phone",
    minPrice: 700,
    query: "premium phone with great camera and OLED display",
    tone: "emerald",
  },
  {
    id: "family-tablet",
    title: "Tablet for parents",
    subtitle: "Easy reading, video calls, big screen.",
    category: "tablet",
    query: "tablet for casual reading, family video calls, and light browsing",
    tone: "amber",
  },
  {
    id: "travel-earbuds",
    title: "Travel earbuds with ANC",
    subtitle: "Noise cancellation and long battery for flights.",
    category: "earbuds",
    maxPrice: 500,
    query: "travel earbuds with active noise cancellation and long battery life",
    tone: "rose",
  },
  {
    id: "designer-monitor",
    title: "Designer's monitor",
    subtitle: "Color-accurate panel for design and editing.",
    category: "monitor",
    query: "monitor for design work with accurate color and high refresh rate",
    tone: "sky",
  },
  {
    id: "compare-phones",
    title: "Compare two phones",
    subtitle: "Side-by-side spec sheet and trade-offs.",
    category: "phone",
    query: "compare flagship phones across camera, battery, and price",
    tone: "violet",
  },
];

const INITIAL_FILTER: FilterState = {
  category: null,
  priceBandId: "any",
  brand: null,
  refine: "",
};

const INITIAL_ADVISOR: AdvisorState = {
  status: "idle",
  text: "",
  question: "",
  error: null,
  provider: null,
  model: null,
};

async function postSearch(payload: {
  query: string;
  category: string | null;
  minPrice?: number;
  maxPrice?: number;
  brand?: string | null;
  limit: number;
}): Promise<EcommerceSearchResponse> {
  const response = await fetch("/api/preview/ecommerce/search", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: payload.query,
      filters: {
        category: payload.category,
        min_price_usd: payload.minPrice ?? null,
        max_price_usd: payload.maxPrice ?? null,
        brand: payload.brand ?? null,
      },
      limit: payload.limit,
    }),
  });
  if (!response.ok) {
    throw new Error(`Search failed (${response.status})`);
  }
  return (await response.json()) as EcommerceSearchResponse;
}

async function postCompare(productIds: string[]): Promise<EcommerceCompareResponse> {
  const response = await fetch("/api/preview/ecommerce/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_ids: productIds }),
  });
  if (!response.ok) {
    throw new Error(`Compare failed (${response.status})`);
  }
  return (await response.json()) as EcommerceCompareResponse;
}

interface StreamAdvisorOptions {
  query: string;
  signal: AbortSignal;
  onRetrieval(blocks: ProductCardBlock[]): void;
  onDelta(text: string): void;
  onDone(meta: { provider: string; model: string | null }): void;
  onError(message: string): void;
}

async function streamAdvisor(options: StreamAdvisorOptions): Promise<void> {
  let response: Response;
  try {
    response = await fetch("/api/preview/ecommerce/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: options.query, retrieval_limit: 5 }),
      signal: options.signal,
    });
  } catch (caught) {
    if ((caught as { name?: string })?.name === "AbortError") return;
    options.onError(caught instanceof Error ? caught.message : "Network error.");
    return;
  }
  if (!response.ok || !response.body) {
    options.onError(`Advisor failed (${response.status})`);
    return;
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let newlineIndex = buffer.indexOf("\n");
      while (newlineIndex >= 0) {
        const line = buffer.slice(0, newlineIndex).trim();
        buffer = buffer.slice(newlineIndex + 1);
        if (line.length > 0) {
          try {
            const event = JSON.parse(line) as EcommerceChatStreamEvent;
            if (event.type === "retrieval") options.onRetrieval(event.blocks);
            else if (event.type === "delta") options.onDelta(event.text);
            else if (event.type === "done")
              options.onDone({
                provider: event.provider,
                model: event.model ?? null,
              });
          } catch {
            // ignore malformed line
          }
        }
        newlineIndex = buffer.indexOf("\n");
      }
    }
    const tail = buffer.trim();
    if (tail.length > 0) {
      try {
        const event = JSON.parse(tail) as EcommerceChatStreamEvent;
        if (event.type === "retrieval") options.onRetrieval(event.blocks);
        else if (event.type === "delta") options.onDelta(event.text);
        else if (event.type === "done")
          options.onDone({ provider: event.provider, model: event.model ?? null });
      } catch {
        // ignore
      }
    }
  } catch (caught) {
    if ((caught as { name?: string })?.name === "AbortError") return;
    options.onError(caught instanceof Error ? caught.message : "Stream error.");
  }
}

function activePriceBand(priceBandId: string): PriceBand {
  return PRICE_BANDS.find((band) => band.id === priceBandId) ?? PRICE_BANDS[0];
}

export default function ShopperWorkbenchPage() {
  const [filter, setFilter] = useState<FilterState>(INITIAL_FILTER);
  const [taskSeedQuery, setTaskSeedQuery] = useState<string>("");
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [blocks, setBlocks] = useState<ProductCardBlock[]>([]);
  const [totalCount, setTotalCount] = useState<number>(0);
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [selectedById, setSelectedById] = useState<Record<string, ProductCardBlock>>({});
  const [compareBlock, setCompareBlock] = useState<SpecCompareBlock | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [compareNotice, setCompareNotice] = useState<string | null>(null);

  const [advisor, setAdvisor] = useState<AdvisorState>(INITIAL_ADVISOR);
  const advisorAbortRef = useRef<AbortController | null>(null);

  const brands = useMemo(() => {
    const set = new Set<string>();
    for (const block of blocks) set.add(block.brand);
    return Array.from(set).sort();
  }, [blocks]);

  const runSearch = useCallback(
    async (currentFilter: FilterState, seed: string) => {
      setIsSearching(true);
      setSearchError(null);
      const band = activePriceBand(currentFilter.priceBandId);
      const refine = currentFilter.refine.trim();
      const baseQuery = seed.trim();
      const query = refine ? `${baseQuery} ${refine}`.trim() : baseQuery;
      try {
        const result = await postSearch({
          query,
          category: currentFilter.category,
          minPrice: band.min,
          maxPrice: band.max,
          brand: currentFilter.brand,
          limit: 12,
        });
        setBlocks(result.blocks);
        setTotalCount(result.total);
      } catch (caught) {
        setSearchError(caught instanceof Error ? caught.message : "Search failed.");
        setBlocks([]);
        setTotalCount(0);
      } finally {
        setIsSearching(false);
      }
    },
    [],
  );

  useEffect(() => {
    void runSearch(filter, taskSeedQuery);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter, taskSeedQuery]);

  const onPickTask = useCallback((entry: TaskEntry) => {
    setActiveTaskId(entry.id);
    setTaskSeedQuery(entry.query);
    setFilter({
      category: entry.category as EcommerceProductCategory | null,
      priceBandId: priceBandIdFor(entry.minPrice, entry.maxPrice),
      brand: null,
      refine: "",
    });
    setCompareBlock(null);
    setCompareNotice(null);
  }, []);

  const blocksRef = useRef<ProductCardBlock[]>([]);
  useEffect(() => {
    blocksRef.current = blocks;
  }, [blocks]);

  const onToggleCompare = useCallback((productId: string) => {
    setSelectedIds((current) => {
      if (current.includes(productId)) {
        setSelectedById((map) => {
          if (!(productId in map)) return map;
          const next = { ...map };
          delete next[productId];
          return next;
        });
        return current.filter((id) => id !== productId);
      }
      if (current.length >= SELECTION_LIMIT) return current;
      const block = blocksRef.current.find((b) => b.product_id === productId);
      if (block) {
        setSelectedById((map) =>
          productId in map ? map : { ...map, [productId]: block },
        );
      }
      return [...current, productId];
    });
    setCompareBlock(null);
    setCompareNotice(null);
  }, []);

  const onClearSelection = useCallback(() => {
    setSelectedIds([]);
    setSelectedById({});
    setCompareBlock(null);
    setCompareNotice(null);
  }, []);

  const runCompare = useCallback(async () => {
    if (selectedIds.length < 2) return;
    setIsComparing(true);
    setCompareNotice(null);
    try {
      const result = await postCompare(selectedIds);
      setCompareBlock(result.block);
      if (result.missing_ids.length > 0) {
        setCompareNotice(
          `Some picks didn't have a record yet: ${result.missing_ids.length}.`,
        );
      }
    } catch (caught) {
      setCompareNotice(
        caught instanceof Error ? caught.message : "Compare failed.",
      );
    } finally {
      setIsComparing(false);
    }
  }, [selectedIds]);

  const askAdvisor = useCallback(
    async (question: string) => {
      const trimmed = question.trim();
      if (!trimmed) return;
      advisorAbortRef.current?.abort();
      const controller = new AbortController();
      advisorAbortRef.current = controller;
      setAdvisor({
        status: "streaming",
        text: "",
        question: trimmed,
        error: null,
        provider: null,
        model: null,
      });
      let accumulated = "";
      await streamAdvisor({
        query: trimmed,
        signal: controller.signal,
        onRetrieval: () => {
          // retrieval blocks intentionally not surfaced — the candidate
          // grid is already the source of truth for "what's available".
        },
        onDelta: (text) => {
          accumulated += text;
          setAdvisor((current) => ({ ...current, text: accumulated }));
        },
        onDone: (meta) => {
          setAdvisor((current) => ({
            ...current,
            status: "done",
            text: accumulated,
            provider: meta.provider,
            model: meta.model,
          }));
        },
        onError: (message) => {
          setAdvisor((current) => ({
            ...current,
            status: "error",
            error: message,
          }));
        },
      });
    },
    [],
  );

  const cancelAdvisor = useCallback(() => {
    advisorAbortRef.current?.abort();
    advisorAbortRef.current = null;
    setAdvisor((current) =>
      current.status === "streaming"
        ? { ...current, status: "done" }
        : current,
    );
  }, []);

  const onClearFilter = useCallback(() => {
    setFilter(INITIAL_FILTER);
    setActiveTaskId(null);
    setTaskSeedQuery("");
  }, []);

  const selectedBlocks = useMemo(
    () =>
      selectedIds
        .map((id) => selectedById[id])
        .filter((b): b is ProductCardBlock => Boolean(b)),
    [selectedById, selectedIds],
  );

  const onAskAboutCard = useCallback(
    (block: ProductCardBlock) => {
      const task = taskSeedQuery || "a 3C purchase decision";
      const question = `Why does the ${block.name} (${block.brand}, ${block.category}) fit "${task}"? Be concrete about specs.`;
      void askAdvisor(question);
    },
    [askAdvisor, taskSeedQuery],
  );

  const onExplainCompare = useCallback(() => {
    if (selectedBlocks.length < 2) return;
    const task = taskSeedQuery || "a 3C purchase decision";
    const names = selectedBlocks.map((b) => b.name).join(" vs ");
    const question = `Compare ${names} for the task "${task}". Walk through trade-offs and recommend one.`;
    void askAdvisor(question);
  }, [askAdvisor, selectedBlocks, taskSeedQuery]);

  useEffect(() => {
    return () => {
      advisorAbortRef.current?.abort();
    };
  }, []);

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-8">
        <header className="flex flex-col gap-1">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            Shopper workbench · v2
          </p>
          <h1 className="text-2xl font-semibold text-slate-950">
            Shop the 3C catalog with an AI advisor
          </h1>
          <p className="max-w-3xl text-sm leading-6 text-slate-600">
            Pick a task to seed the candidates, narrow them down with chips,
            select up to {SELECTION_LIMIT} products to compare, and let the
            advisor explain the trade-offs.
          </p>
        </header>

        <TaskEntries
          entries={TASK_ENTRIES}
          activeEntryId={activeTaskId}
          onPick={onPickTask}
        />

        {searchError && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {searchError}
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)_340px]">
          <FilterSidebar
            filter={filter}
            brands={brands}
            priceBands={PRICE_BANDS}
            onChange={setFilter}
            onClear={onClearFilter}
            visibleCount={blocks.length}
            totalCount={totalCount}
          />

          <div className="flex flex-col gap-3">
            <div className="flex items-baseline justify-between">
              <h2 className="text-sm font-semibold text-slate-950">
                Candidates
                <span className="ml-2 text-xs font-normal text-slate-500">
                  {isSearching
                    ? "Loading…"
                    : `${blocks.length} shown · ${totalCount} matched`}
                </span>
              </h2>
              {activeTaskId && (
                <span className="rounded-full bg-slate-900 px-2.5 py-0.5 text-[11px] font-medium text-white">
                  Task: {TASK_ENTRIES.find((t) => t.id === activeTaskId)?.title}
                </span>
              )}
            </div>
            <ProductGrid
              blocks={blocks}
              selectedIds={selectedIds}
              selectionLimit={SELECTION_LIMIT}
              onToggleCompare={onToggleCompare}
              onAskAdvisor={onAskAboutCard}
              isLoading={isSearching}
            />
          </div>

          <div className="flex flex-col gap-4">
            <CompareTray
              selectedBlocks={selectedBlocks}
              compareBlock={compareBlock}
              isComparing={isComparing}
              compareNotice={compareNotice}
              onRemove={onToggleCompare}
              onClear={onClearSelection}
              onCompare={runCompare}
              onExplain={onExplainCompare}
            />
            <AdvisorPanel
              state={advisor}
              selectedBlocks={selectedBlocks}
              taskSeedQuery={taskSeedQuery}
              onAsk={askAdvisor}
              onAskCustom={askAdvisor}
              onCancel={cancelAdvisor}
            />
          </div>
        </div>
      </div>
    </main>
  );
}

function priceBandIdFor(min: number | undefined, max: number | undefined): string {
  if (min == null && max == null) return "any";
  for (const band of PRICE_BANDS) {
    if (band.min === min && band.max === max) return band.id;
  }
  // Fall back to the closest matching cap.
  if (max != null && max <= 500) return "lt500";
  if (max != null && max <= 1000) return "500-1000";
  if (max != null && max <= 1500) return "1000-1500";
  if (min != null && min >= 1500) return "1500-plus";
  return "any";
}
