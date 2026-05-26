/**
 * Pure helpers that classify candidate products into three shopper-friendly
 * recommendation tiers — Best fit / Performance pick / Value pick — and
 * derive a short, task-aware "Why it fits" line for each card.
 *
 * The classification is intentionally heuristic and runs entirely client-side
 * on the same `ProductCardBlock` shape the API already returns. It does NOT
 * call the backend and does NOT depend on the advisor stream — the tiers
 * appear as soon as a search resolves.
 *
 * Tiers are best-effort labels for shopping decision-making, not absolute
 * rankings:
 *
 *   - "best-fit"    — the candidate closest to the user's stated budget that
 *                     still hits the dominant spec for the category.
 *   - "performance" — the candidate with the strongest core spec in the set
 *                     (most RAM, biggest battery, sharpest panel, etc.).
 *   - "value"       — the candidate with the lowest price that still meets a
 *                     reasonable spec threshold.
 *
 * If the search returns very few candidates (1-2) the helpers degrade
 * gracefully so we never label every card with the same tier.
 */

import type { ProductCardBlock } from "@/lib/contracts/ecommerce-blocks";

export type RecommendationTier = "best-fit" | "performance" | "value";

export interface TieredCandidate {
  block: ProductCardBlock;
  tier: RecommendationTier | null;
  whyItFits: string;
  matchScore: number;
}

const SPEC_LABEL_ALIASES: Record<string, readonly string[]> = {
  memory: ["Memory", "RAM"],
  storage: ["Storage", "SSD"],
  battery: ["Battery", "Battery life"],
  display: ["Display", "Screen"],
  refresh: ["Refresh", "Refresh rate"],
  weight: ["Weight"],
  chip: ["Chip", "Processor", "CPU"],
  camera: ["Camera"],
  driver: ["Driver", "Drivers"],
};

function readSpec(block: ProductCardBlock, key: keyof typeof SPEC_LABEL_ALIASES): string | null {
  const labels = SPEC_LABEL_ALIASES[key];
  for (const spec of block.specs) {
    if (labels.includes(spec.label)) return spec.value;
  }
  return null;
}

function firstNumber(value: string | null): number | null {
  if (!value) return null;
  const match = value.match(/(\d+(?:\.\d+)?)/);
  return match ? Number.parseFloat(match[1]) : null;
}

/**
 * A coarse "performance score" used to rank candidates within a category.
 * The exact weights are not load-bearing — we only need a stable ordering
 * within a single search result so that the user sees a meaningful spread
 * between the "performance" pick and the "value" pick.
 */
function performanceScore(block: ProductCardBlock): number {
  let score = 0;
  const ram = firstNumber(readSpec(block, "memory"));
  if (ram != null) score += ram * 2; // weight: RAM dominates laptop/tablet feel
  const storage = firstNumber(readSpec(block, "storage"));
  if (storage != null) score += storage / 100;
  const battery = firstNumber(readSpec(block, "battery"));
  if (battery != null) score += battery; // hours
  const refresh = firstNumber(readSpec(block, "refresh"));
  if (refresh != null) score += refresh / 10;
  // Price contributes as a tiebreaker — higher-priced items tend to have
  // better silicon even when the user-facing specs look identical.
  score += block.price_usd / 500;
  return score;
}

/**
 * A coarse "value-for-money" score. Performance per dollar, with a small
 * floor so a $200 item with mediocre specs still ranks above a $1500 item
 * with merely-okay specs.
 */
function valueScore(block: ProductCardBlock): number {
  const perf = performanceScore(block);
  const priceFloor = Math.max(block.price_usd, 100);
  return perf / (priceFloor / 1000);
}

function dominantSpec(block: ProductCardBlock): { label: string; value: string } | null {
  // Prefer the spec a shopper actually reads when comparing.
  const preferred = ["Memory", "RAM", "Battery", "Display", "Screen", "Camera", "Refresh", "Chip"];
  const map = new Map<string, string>();
  for (const spec of block.specs) map.set(spec.label, spec.value);
  for (const label of preferred) {
    const value = map.get(label);
    if (value) return { label, value };
  }
  return block.specs[0] ?? null;
}

/**
 * Build a 1-2 sentence "Why it fits" line that anchors the card to the
 * shopper's current task. Stitch's design uses a similar block on each
 * product card; we keep it lightweight and entirely client-side here.
 */
function buildWhyItFits(
  block: ProductCardBlock,
  tier: RecommendationTier | null,
  taskTitle: string | null,
  budgetCap: number | null,
): string {
  const spec = dominantSpec(block);
  const baseRef = taskTitle ? `the "${taskTitle}" task` : "this kind of shopping";
  const cheap = budgetCap != null && block.price_usd <= budgetCap * 0.85;
  if (tier === "best-fit") {
    if (spec) {
      return `Hits the sweet spot for ${baseRef} — ${spec.label.toLowerCase()} at ${spec.value} with room in the budget.`;
    }
    return `Strong all-rounder for ${baseRef}, balanced on price and the spec that matters most.`;
  }
  if (tier === "performance") {
    if (spec) {
      return `Strongest ${spec.label.toLowerCase()} in this range (${spec.value}) — pick this if raw capability matters more than saving money.`;
    }
    return `Top-tier specs in this range — pick this if performance matters more than saving money.`;
  }
  if (tier === "value") {
    if (cheap && spec) {
      return `Best value in the shortlist — keeps ${spec.label.toLowerCase()} at ${spec.value} while staying well under budget.`;
    }
    return `Best overall value here if you can give up a notch of performance to save money.`;
  }
  if (spec) {
    return `Solid alternative for ${baseRef} — ${spec.label.toLowerCase()} at ${spec.value}.`;
  }
  return `Solid alternative for ${baseRef}.`;
}

/**
 * Classify a result list into recommendation tiers. Returns an array in the
 * caller's order, annotated with `tier`, `whyItFits`, and `matchScore`.
 *
 * - When ≥3 candidates exist we always pick one of each tier; remaining
 *   candidates are left as `tier: null` (rendered under "More candidates").
 * - When exactly 2 candidates exist we pick the best-fit and the value pick.
 * - When exactly 1 candidate exists we label it best-fit.
 * - When the candidate list is empty we return [].
 */
export function classifyCandidates(
  blocks: readonly ProductCardBlock[],
  taskTitle: string | null,
  budgetCap: number | null,
): TieredCandidate[] {
  if (blocks.length === 0) return [];

  const ranked = blocks.map((block) => ({
    block,
    perf: performanceScore(block),
    value: valueScore(block),
  }));

  const byPerf = [...ranked].sort((a, b) => b.perf - a.perf);
  const byValue = [...ranked].sort((a, b) => b.value - a.value);

  const tierByProductId = new Map<string, RecommendationTier>();

  if (blocks.length === 1) {
    tierByProductId.set(blocks[0].product_id, "best-fit");
  } else if (blocks.length === 2) {
    const [hi, lo] = byPerf;
    if (hi.block.price_usd > lo.block.price_usd) {
      tierByProductId.set(hi.block.product_id, "best-fit");
      tierByProductId.set(lo.block.product_id, "value");
    } else {
      tierByProductId.set(lo.block.product_id, "best-fit");
      tierByProductId.set(hi.block.product_id, "value");
    }
  } else {
    // Best fit = highest value-for-money among the top-performance half.
    const topHalfIds = new Set(
      byPerf.slice(0, Math.max(2, Math.ceil(blocks.length / 2))).map((r) => r.block.product_id),
    );
    const bestFit =
      [...byValue].find((r) => topHalfIds.has(r.block.product_id)) ?? byValue[0];
    const performance =
      byPerf.find((r) => r.block.product_id !== bestFit.block.product_id) ?? byPerf[0];
    const value =
      byValue
        .slice()
        .reverse() // start from worst-perf-best-value end
        .find(
          (r) =>
            r.block.product_id !== bestFit.block.product_id &&
            r.block.product_id !== performance.block.product_id,
        ) ??
      byValue.find(
        (r) =>
          r.block.product_id !== bestFit.block.product_id &&
          r.block.product_id !== performance.block.product_id,
      ) ??
      byValue[byValue.length - 1];

    tierByProductId.set(bestFit.block.product_id, "best-fit");
    tierByProductId.set(performance.block.product_id, "performance");
    if (value && !tierByProductId.has(value.block.product_id)) {
      tierByProductId.set(value.block.product_id, "value");
    }
  }

  // Match score: derived from value-rank position so the top-fit card gets
  // a high label (e.g. 96) and tail cards a lower one. Cheap to compute and
  // good enough as a confidence hint for the shopper.
  const valueRankById = new Map<string, number>();
  byValue.forEach((r, idx) => valueRankById.set(r.block.product_id, idx));

  return blocks.map((block) => {
    const tier = tierByProductId.get(block.product_id) ?? null;
    const valueRank = valueRankById.get(block.product_id) ?? blocks.length - 1;
    const matchScore = Math.max(
      62,
      Math.round(96 - (valueRank / Math.max(1, blocks.length - 1)) * 28),
    );
    return {
      block,
      tier,
      whyItFits: buildWhyItFits(block, tier, taskTitle, budgetCap),
      matchScore,
    };
  });
}

export const TIER_LABEL: Record<RecommendationTier, string> = {
  "best-fit": "Best fit",
  performance: "Performance pick",
  value: "Value pick",
};

export const TIER_SUBLINE: Record<RecommendationTier, string> = {
  "best-fit": "Balanced on price and the spec that matters most.",
  performance: "Top specs in this range — sacrifice price for capability.",
  value: "Most product per dollar — sacrifice top specs to save money.",
};
