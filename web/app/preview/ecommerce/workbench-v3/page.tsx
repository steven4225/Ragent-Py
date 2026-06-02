"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";

import { AdvisorBriefBar } from "@/components/ecommerce/workbench-v3/advisor-brief-bar";
import { AlternativeLanes } from "@/components/ecommerce/workbench-v3/alternative-lanes";
import { CatalogDrawer } from "@/components/ecommerce/workbench-v3/catalog-drawer";
import { DecisionMemoPanel } from "@/components/ecommerce/workbench-v3/decision-memo-panel";
import { IntentInterpretationStrip } from "@/components/ecommerce/workbench-v3/intent-interpretation-strip";
import { PrimaryVerdictPanel } from "@/components/ecommerce/workbench-v3/primary-verdict-panel";
import { TradeoffCompareBoard } from "@/components/ecommerce/workbench-v3/tradeoff-compare-board";
import type { AdvisorState, FilterState } from "@/components/ecommerce/workbench/types";
import type {
  EcommerceChatStreamEvent,
  EcommerceCompareResponse,
  EcommerceSearchResponse,
  ProductCardBlock,
  SpecCompareBlock,
} from "@/lib/contracts/ecommerce-blocks";
import {
  localCompare,
  localRecommendationText,
  localSearch,
  parseBrief,
} from "@/lib/ecommerce/local-decision-engine";
import {
  buildAlternativeLanes,
  buildCompareHighlights,
  buildDecisionMemo,
  buildIntentInterpretation,
  buildPrimaryVerdict,
} from "@/lib/ecommerce/workbench-v3-view-model";
import {
  WORKBENCH_PRICE_BANDS,
  WORKBENCH_TASKS,
  getWorkbenchTaskById,
  seedFilterFromTask,
  stageForWorkbenchState,
} from "@/lib/ecommerce/workbench-seed";

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

type DataMode = "backend" | "local";

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

async function streamAdvisor(options: {
  query: string;
  signal: AbortSignal;
  onDelta(text: string): void;
  onDone(meta: { provider: string; model: string | null }): void;
  onError(message: string): void;
}): Promise<void> {
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
    await streamLocalAdvisor(options);
    return;
  }

  if (!response.ok || !response.body) {
    await streamLocalAdvisor(options);
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
            if (event.type === "delta") {
              options.onDelta(event.text);
            } else if (event.type === "done") {
              options.onDone({
                provider: event.provider,
                model: event.model ?? null,
              });
            }
          } catch {
            // Ignore malformed event lines from the preview stream.
          }
        }

        newlineIndex = buffer.indexOf("\n");
      }
    }
  } catch (caught) {
    if ((caught as { name?: string })?.name === "AbortError") return;
    options.onError(caught instanceof Error ? caught.message : "Decision note failed.");
  }
}

async function streamLocalAdvisor(options: {
  query: string;
  signal: AbortSignal;
  onDelta(text: string): void;
  onDone(meta: { provider: string; model: string | null }): void;
}): Promise<void> {
  const text = localRecommendationText(options.query);
  const chunks = text.match(/.{1,80}(\s|$)/g) ?? [text];

  for (const chunk of chunks) {
    if (options.signal.aborted) return;
    options.onDelta(chunk);
    await new Promise((resolve) => setTimeout(resolve, 24));
  }

  options.onDone({ provider: "local_decision_engine", model: "fallback-catalog" });
}

function activePriceBand(priceBandId: string) {
  return (
    WORKBENCH_PRICE_BANDS.find((band) => band.id === priceBandId) ??
    WORKBENCH_PRICE_BANDS[0]
  );
}

function toFilterCategory(value: string | null): FilterState["category"] {
  if (
    value === "laptop" ||
    value === "phone" ||
    value === "tablet" ||
    value === "earbuds" ||
    value === "monitor"
  ) {
    return value;
  }

  return null;
}

export default function ShopperWorkbenchV3Page() {
  const searchParams = useSearchParams();

  const [filter, setFilter] = useState<FilterState>(INITIAL_FILTER);
  const [draftBrief, setDraftBrief] = useState("");
  const [committedBrief, setCommittedBrief] = useState("");
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [blocks, setBlocks] = useState<ProductCardBlock[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [dataMode, setDataMode] = useState<DataMode>("backend");
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [selectedById, setSelectedById] = useState<Record<string, ProductCardBlock>>({});
  const [compareBlock, setCompareBlock] = useState<SpecCompareBlock | null>(null);
  const [isComparing, setIsComparing] = useState(false);

  const [advisor, setAdvisor] = useState<AdvisorState>(INITIAL_ADVISOR);
  const advisorAbortRef = useRef<AbortController | null>(null);
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [bootstrapped, setBootstrapped] = useState(false);

  const workingBrief = committedBrief || draftBrief || "current shopping request";
  const parsedBrief = useMemo(() => parseBrief(workingBrief), [workingBrief]);

  const selectedBlocks = useMemo(
    () =>
      selectedIds
        .map((id) => selectedById[id])
        .filter((block): block is ProductCardBlock => Boolean(block)),
    [selectedById, selectedIds],
  );

  const currentStage = useMemo(
    () =>
      stageForWorkbenchState(
        selectedBlocks.length,
        Boolean(compareBlock),
        advisor.status === "streaming" || advisor.text.trim().length > 0,
      ),
    [advisor.status, advisor.text, compareBlock, selectedBlocks.length],
  );

  const intent = useMemo(
    () => buildIntentInterpretation(workingBrief, currentStage),
    [currentStage, workingBrief],
  );

  const verdict = useMemo(
    () => buildPrimaryVerdict(blocks, workingBrief),
    [blocks, workingBrief],
  );

  const lanes = useMemo(
    () => buildAlternativeLanes(blocks, workingBrief),
    [blocks, workingBrief],
  );

  const compareHighlights = useMemo(
    () =>
      selectedBlocks.length >= 2
        ? buildCompareHighlights(selectedBlocks[0], selectedBlocks[1])
        : [],
    [selectedBlocks],
  );

  const memo = useMemo(
    () => buildDecisionMemo(verdict, selectedBlocks[1] ?? lanes[0]?.block ?? null),
    [lanes, selectedBlocks, verdict],
  );

  const rememberBlocks = useCallback((nextBlocks: ProductCardBlock[]) => {
    setSelectedById((current) => {
      const merged = { ...current };
      for (const block of nextBlocks) {
        merged[block.product_id] = block;
      }
      return merged;
    });
  }, []);

  const askAdvisor = useCallback(async (question: string) => {
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
  }, []);

  const runSearch = useCallback(
    async (nextFilter: FilterState, nextBrief: string) => {
      const query = nextBrief.trim();
      if (!query) return;

      const band = activePriceBand(nextFilter.priceBandId);

      setIsSearching(true);
      setSearchError(null);
      setSelectedIds([]);
      setCompareBlock(null);
      setCatalogOpen(false);

      try {
        const result = await postSearch({
          query,
          category: nextFilter.category,
          minPrice: band.min,
          maxPrice: band.max,
          brand: nextFilter.brand,
          limit: 12,
        });
        setBlocks(result.blocks);
        setTotalCount(result.total);
        setDataMode("backend");
        rememberBlocks(result.blocks);
      } catch {
        const fallback = localSearch({
          query,
          category: nextFilter.category,
          minPrice: band.min,
          maxPrice: band.max,
          brand: nextFilter.brand,
          limit: 12,
        });
        setBlocks(fallback.blocks);
        setTotalCount(fallback.total);
        setDataMode("local");
        rememberBlocks(fallback.blocks);
      } finally {
        setIsSearching(false);
      }
    },
    [rememberBlocks],
  );

  const runCompare = useCallback(
    async (candidate: ProductCardBlock | null) => {
      const winner = verdict.winner;
      if (!winner || !candidate) return;

      const ids =
        winner.product_id === candidate.product_id
          ? [winner.product_id]
          : [winner.product_id, candidate.product_id];

      rememberBlocks([winner, candidate]);
      setSelectedIds(ids);

      if (ids.length < 2) {
        setCompareBlock(null);
        return;
      }

      setIsComparing(true);
      try {
        const result = await postCompare(ids);
        setCompareBlock(result.block);
      } catch {
        const fallback = localCompare(ids);
        setCompareBlock(fallback.block);
      } finally {
        setIsComparing(false);
      }

      void askAdvisor(
        `Compare ${winner.name} and ${candidate.name} for "${workingBrief}". Explain the trade-off and confirm which one better fits the brief.`,
      );
    },
    [askAdvisor, rememberBlocks, verdict.winner, workingBrief],
  );

  const submitBrief = useCallback(
    (nextBrief: string) => {
      const normalized = nextBrief.trim();
      if (!normalized) return;

      const nextParsed = parseBrief(normalized);
      const nextFilter: FilterState = {
        ...filter,
        category: toFilterCategory(nextParsed.category) ?? filter.category,
      };

      setActiveTaskId(null);
      setFilter(nextFilter);
      setDraftBrief(normalized);
      setCommittedBrief(normalized);
      void runSearch(nextFilter, normalized);
    },
    [filter, runSearch],
  );

  const onSubmitBrief = useCallback(() => {
    submitBrief(draftBrief);
  }, [draftBrief, submitBrief]);

  const onPickReference = useCallback(
    (taskId: string) => {
      const task = getWorkbenchTaskById(taskId);
      if (!task) return;

      const nextFilter = seedFilterFromTask(task);
      setActiveTaskId(task.id);
      setFilter(nextFilter);
      setDraftBrief(task.query);
      setCommittedBrief(task.query);
      void runSearch(nextFilter, task.query);
    },
    [runSearch],
  );

  useEffect(() => {
    if (bootstrapped) return;

    const taskId = searchParams.get("task");
    const task = getWorkbenchTaskById(taskId) ?? WORKBENCH_TASKS[0];
    const nextFilter = seedFilterFromTask(task);

    setActiveTaskId(task.id);
    setFilter(nextFilter);
    setDraftBrief(task.query);
    setCommittedBrief(task.query);
    setBootstrapped(true);
    void runSearch(nextFilter, task.query);
  }, [bootstrapped, runSearch, searchParams]);

  useEffect(() => {
    return () => {
      advisorAbortRef.current?.abort();
    };
  }, []);

  const dataModeLabel =
    dataMode === "backend" ? "Backend catalog" : "Local fallback catalog";

  const referenceBriefs = useMemo(
    () =>
      WORKBENCH_TASKS.map((task) => ({
        id: task.id,
        title: task.title,
        subtitle: task.subtitle,
      })),
    [],
  );

  return (
    <main className="min-h-screen bg-[#f1eee6] text-slate-950">
      <div className="mx-auto flex w-full max-w-[1380px] flex-col gap-4 px-4 py-5 sm:px-6 lg:px-8">
        {searchError ? (
          <div className="border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {searchError}
          </div>
        ) : null}

        <AdvisorBriefBar
          brief={draftBrief}
          budgetLabel={parsedBrief.budgetLabel}
          useCase={parsedBrief.useCase}
          mustHaves={parsedBrief.mustHaves}
          niceToHaves={parsedBrief.niceToHaves}
          warnings={parsedBrief.warnings}
          disabled={isSearching}
          dataModeLabel={dataModeLabel}
          referenceBriefs={referenceBriefs}
          activeReferenceId={activeTaskId}
          onBriefChange={setDraftBrief}
          onSubmit={onSubmitBrief}
          onPickReference={onPickReference}
        />

        <IntentInterpretationStrip {...intent} />

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_360px]">
          <PrimaryVerdictPanel
            verdict={verdict}
            onInspectCompare={() => void runCompare(lanes[0]?.block ?? null)}
            onInspectAlternatives={() => setCatalogOpen(true)}
          />
          <DecisionMemoPanel memo={memo} />
        </div>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <AlternativeLanes
            lanes={lanes}
            onChooseLane={(lane) => void runCompare(lane.block)}
          />
          <TradeoffCompareBoard
            highlights={compareHighlights}
            compareBlock={compareBlock}
          />
        </div>

        <CatalogDrawer
          open={catalogOpen}
          onToggle={() => setCatalogOpen((current) => !current)}
          summary="Use the wider field to challenge the current recommendation, not to restart from zero."
        >
          <div className="border-b border-slate-200 pb-3">
            <div className="grid gap-3 md:grid-cols-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Candidate pool
                </p>
                <p className="mt-2 text-sm text-slate-950">
                  {isSearching ? "Refreshing the shortlist..." : `${blocks.length} shown / ${totalCount} matched`}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Compare state
                </p>
                <p className="mt-2 text-sm text-slate-950">
                  {selectedBlocks.length >= 2
                    ? `${selectedBlocks[0].name} vs ${selectedBlocks[1].name}`
                    : "No active trade-off selected yet"}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                  Flow stage
                </p>
                <p className="mt-2 text-sm text-slate-950">{currentStage}</p>
              </div>
            </div>
          </div>

          <div className="divide-y divide-slate-200">
            {blocks.map((block) => {
              const isWinner = verdict.winner?.product_id === block.product_id;
              return (
                <article
                  key={block.product_id}
                  className="grid gap-4 py-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-start"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="text-lg font-semibold tracking-tight text-slate-950">
                        {block.name}
                      </h3>
                      <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                        {block.brand}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-slate-600">
                      {block.category} / ${block.price_usd.toLocaleString("en-US")} / {block.release_year}
                    </p>
                    <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-700">
                      {block.summary}
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {block.specs.slice(0, 4).map((spec) => (
                        <span
                          key={`${block.product_id}:${spec.label}`}
                          className="border border-slate-200 bg-slate-50 px-2 py-1 text-xs text-slate-600"
                        >
                          {spec.label}: {spec.value}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => void runCompare(block)}
                      disabled={isWinner || isComparing}
                      className="border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-700 transition-colors duration-150 hover:border-slate-500 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
                    >
                      {isWinner ? "Current winner" : "Compare with winner"}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </CatalogDrawer>
      </div>
    </main>
  );
}
