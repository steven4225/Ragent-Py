"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { AdvisorPanel } from "@/components/ecommerce/workbench/advisor-panel";
import {
  CompareTray,
  SELECTION_LIMIT,
} from "@/components/ecommerce/workbench/compare-tray";
import { FilterSidebar } from "@/components/ecommerce/workbench/filter-sidebar";
import { ProductGrid } from "@/components/ecommerce/workbench/product-grid";
import {
  classifyCandidates,
  type TieredCandidate,
} from "@/components/ecommerce/workbench/recommendation";
import {
  StageIndicator,
  type WorkbenchStage,
} from "@/components/ecommerce/workbench/stage-indicator";
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
 * Shopper decision workbench.
 *
 * Page protagonist is the candidate shortlist + the spec-table comparison —
 * not a chat box, not an AI console. The workbench reads top-down as:
 *
 *   1. Header — current task title, stage indicator (Explore / Compare /
 *      Decide), and a quick status pill so the shopper always knows where
 *      they are in the decision flow.
 *   2. Task entries — 6 starting points that seed the task + filters in
 *      one tap.
 *   3. Left rail — Active task + Active filters + Refine controls.
 *   4. Centre — candidate main stage with recommendation tiers
 *      (Best fit / Performance pick / Value pick) and a "Why it fits"
 *      line on every card.
 *   5. Right rail — Decision core (shortlist + side-by-side spec table)
 *      and a Decision assistant that explains trade-offs anchored to the
 *      shortlist.
 *
 * The wire layer is intentionally untouched: same
 * `/api/preview/ecommerce/{search,compare,chat/stream}` endpoints, same
 * `ProductCardBlock` / `SpecCompareBlock` shapes, same `SpecCompareTable`
 * primitive. The upgrade is purely presentational — Python, the main chat
 * service, and `/api/chat/*` are not touched.
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

  // Bootstrap pass: read ?task= from the URL once on mount, seed the
  // filter + advisor query, then unlock the search effect. We gate the
  // search effect on this flag so that landing on
  // /preview/ecommerce/workbench-v2?task=work-laptop does not first
  // fire a useless empty-state search before the URL-driven task takes
  // over.
  const [bootstrapped, setBootstrapped] = useState<boolean>(false);

  const brands = useMemo(() => {
    const set = new Set<string>();
    for (const block of blocks) set.add(block.brand);
    return Array.from(set).sort();
  }, [blocks]);

  const activeTask = useMemo(
    () => TASK_ENTRIES.find((entry) => entry.id === activeTaskId) ?? null,
    [activeTaskId],
  );

  const activeBand = useMemo(
    () => activePriceBand(filter.priceBandId),
    [filter.priceBandId],
  );

  const candidates: TieredCandidate[] = useMemo(
    () =>
      classifyCandidates(
        blocks,
        activeTask?.title ?? null,
        activeBand.max ?? activeTask?.maxPrice ?? null,
      ),
    [blocks, activeTask, activeBand],
  );

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
    if (bootstrapped) return;
    const params = new URLSearchParams(window.location.search);
    const taskId = params.get("task");
    const entry = taskId
      ? TASK_ENTRIES.find((candidate) => candidate.id === taskId)
      : null;
    if (entry) {
      setActiveTaskId(entry.id);
      setTaskSeedQuery(entry.query);
      setFilter({
        category: entry.category as EcommerceProductCategory | null,
        priceBandId: priceBandIdFor(entry.minPrice, entry.maxPrice),
        brand: null,
        refine: "",
      });
    }
    setBootstrapped(true);
  }, [bootstrapped]);

  useEffect(() => {
    if (!bootstrapped) return;
    void runSearch(filter, taskSeedQuery);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bootstrapped, filter, taskSeedQuery]);

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

  const stage: WorkbenchStage = useMemo(() => {
    if (compareBlock) return "decide";
    if (selectedIds.length >= 2) return "compare";
    return "explore";
  }, [compareBlock, selectedIds.length]);

  const isBusy =
    isSearching || isComparing || advisor.status === "streaming";
  const busyLabel = isComparing
    ? "Building spec table"
    : advisor.status === "streaming"
      ? "Decision assistant thinking"
      : isSearching
        ? "Reading the catalog"
        : null;

  const candidateSummary = activeTask
    ? `Top picks for ${activeTask.title.toLowerCase()}.`
    : filter.category
      ? `Top picks across ${filter.category}s.`
      : "Top picks across the catalog.";

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-100">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-8">
        <header className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
            <div className="flex flex-col gap-1.5">
              <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.22em] text-cyan-700">
                Shopper decision workbench
              </p>
              <h1 className="text-2xl font-semibold tracking-tight text-slate-950 md:text-3xl">
                {activeTask
                  ? activeTask.title
                  : "What are you shopping for today?"}
              </h1>
              <p className="max-w-3xl text-sm leading-6 text-slate-600">
                {activeTask
                  ? activeTask.subtitle
                  : `Pick a task to seed the shortlist, narrow it with chips, hold up to ${SELECTION_LIMIT} picks side-by-side, and let the assistant explain the trade-offs.`}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span
                className={[
                  "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 font-mono text-[10px] font-semibold uppercase tracking-[0.18em]",
                  isBusy
                    ? "border-cyan-300 bg-cyan-50 text-cyan-800"
                    : "border-slate-200 bg-slate-50 text-slate-500",
                ].join(" ")}
                aria-live="polite"
              >
                <span
                  aria-hidden
                  className={[
                    "relative inline-flex h-2 w-2 rounded-full",
                    isBusy ? "bg-cyan-500" : "bg-slate-300",
                  ].join(" ")}
                >
                  {isBusy && (
                    <span className="absolute inset-0 animate-ping rounded-full bg-cyan-400/70" />
                  )}
                </span>
                {busyLabel ?? "Idle"}
              </span>
            </div>
          </div>

          {activeTask && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Active task
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-slate-50 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-slate-700">
                <span className="text-slate-500">Category:</span>
                <span className="text-slate-900">{activeTask.category ?? "any"}</span>
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-slate-50 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-slate-700">
                <span className="text-slate-500">Budget:</span>
                <span className="text-slate-900">{activeBand.label}</span>
              </span>
              {filter.brand && (
                <span className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-slate-50 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-slate-700">
                  <span className="text-slate-500">Brand:</span>
                  <span className="text-slate-900">{filter.brand}</span>
                </span>
              )}
              {filter.refine.trim() && (
                <span className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 bg-slate-50 px-2 py-1 font-mono text-[10px] uppercase tracking-[0.14em] text-slate-700">
                  <span className="text-slate-500">Refine:</span>
                  <span className="text-slate-900">{filter.refine.trim()}</span>
                </span>
              )}
            </div>
          )}

          <StageIndicator stage={stage} />
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
            activeTaskTitle={activeTask?.title ?? null}
            activeTaskSubtitle={activeTask?.subtitle ?? null}
          />

          <div className="flex flex-col gap-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.22em] text-cyan-700">
                    Candidates · main stage
                  </span>
                  <span
                    aria-hidden
                    className="inline-block h-1.5 w-1.5 rounded-full bg-cyan-500"
                  />
                  <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">
                    {isSearching
                      ? "refreshing shortlist…"
                      : `${blocks.length} on stage · ${totalCount} matched`}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  {activeTask && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-slate-950 px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-cyan-300">
                      Task · {activeTask.title}
                    </span>
                  )}
                  {!activeTask && filter.category && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-white px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-700">
                      Category · {filter.category}
                    </span>
                  )}
                  <span className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-white px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-700">
                    Budget · {activeBand.label}
                  </span>
                </div>
              </div>
              <p className="mt-2 text-[12.5px] leading-snug text-slate-600">
                {candidateSummary} Tiers are derived from price and spec balance — the
                <span className="font-semibold text-slate-800"> Best fit</span> card is
                the recommended starting point, then
                <span className="font-semibold text-slate-800"> Performance pick</span>{" "}
                and
                <span className="font-semibold text-slate-800"> Value pick</span> show the
                trade-off either way.
              </p>
            </div>
            <ProductGrid
              candidates={candidates}
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
