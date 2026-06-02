import type { ProductCardBlock } from "@/lib/contracts/ecommerce-blocks";

export type IntentInterpretation = {
  buyingTask: string;
  priorityLine: string;
  advisorPath: string;
  riskNote: string;
};

export type PrimaryVerdict = {
  winner: ProductCardBlock | null;
  why: string;
  notIdealFor: string;
  mainTradeoff: string;
};

export type AlternativeLane = {
  lane: "Save money" | "Push performance";
  block: ProductCardBlock | null;
  why: string;
};

export type CompareHighlightRow = {
  label: "Price" | "Performance" | "Battery" | "Portability" | "Risk";
  primaryValue: string;
  alternativeValue: string;
  verdict: string;
};

export type DecisionMemo = {
  recommendation: string;
  buyIf: string;
  avoidIf: string;
  tradeOff: string;
  revisitWhen: string;
};

export function buildIntentInterpretation(
  brief: string,
  stage: "explore" | "compare" | "decide",
): IntentInterpretation {
  const lower = brief.toLowerCase();
  return {
    buyingTask: "First-pass guided selection",
    priorityLine: lower.includes("under $")
      ? "Budget > battery > performance"
      : "Fit > trade-off clarity > price",
    advisorPath:
      stage === "compare"
        ? "Settle the active trade-off and finish with a recommendation memo."
        : "Recommend one winner first, then compare two controlled alternatives.",
    riskNote: lower.includes("gaming")
      ? "This brief still reads like a balanced machine request, not a pure gaming laptop search."
      : "Avoid expanding into full catalog scanning before the winner is framed.",
  };
}

export function buildPrimaryVerdict(
  blocks: ProductCardBlock[],
  brief: string,
): PrimaryVerdict {
  const winner = blocks[0] ?? null;
  return {
    winner,
    why: winner
      ? `${winner.name} is the most balanced answer for ${brief}.`
      : `No current winner is available yet for ${brief}.`,
    notIdealFor: "Users who care more about max raw performance than everyday balance.",
    mainTradeoff: "You are accepting a balanced all-round pick instead of pushing one dimension to the limit.",
  };
}

export function buildAlternativeLanes(
  blocks: ProductCardBlock[],
  brief: string,
): AlternativeLane[] {
  const fallback = blocks[0] ?? null;
  return [
    {
      lane: "Save money",
      block: blocks[1] ?? fallback,
      why: `Choose this if ${brief} still matters, but total spend matters more than polish.`,
    },
    {
      lane: "Push performance",
      block: blocks[2] ?? fallback,
      why: `Choose this if you are willing to pay more to improve headroom for the same brief.`,
    },
  ];
}

function readSpecValue(block: ProductCardBlock, label: string): string {
  return block.specs.find((spec) => spec.label === label)?.value ?? "-";
}

function readLeadingNumber(value: string): number | null {
  const match = value.match(/(\d+(?:\.\d+)?)/);
  return match ? Number(match[1]) : null;
}

function readNumericSpec(block: ProductCardBlock, label: string): number | null {
  return readLeadingNumber(readSpecValue(block, label));
}

function readMemoryGb(block: ProductCardBlock): number {
  return readNumericSpec(block, "Memory") ?? 0;
}

function readStorageGb(block: ProductCardBlock): number {
  const value = readSpecValue(block, "Storage");
  const amount = readLeadingNumber(value);
  if (amount == null) return 0;
  return /\btb\b/i.test(value) ? amount * 1024 : amount;
}

function performanceScore(block: ProductCardBlock): number {
  return readMemoryGb(block) * 10 + readStorageGb(block) / 128;
}

export function buildCompareHighlights(
  primary: ProductCardBlock,
  alternative: ProductCardBlock,
): CompareHighlightRow[] {
  const primaryBattery = readSpecValue(primary, "Battery");
  const alternativeBattery = readSpecValue(alternative, "Battery");
  const primaryWeight = readSpecValue(primary, "Weight");
  const alternativeWeight = readSpecValue(alternative, "Weight");
  const primaryBatteryValue = readNumericSpec(primary, "Battery");
  const alternativeBatteryValue = readNumericSpec(alternative, "Battery");
  const primaryWeightValue = readNumericSpec(primary, "Weight");
  const alternativeWeightValue = readNumericSpec(alternative, "Weight");
  const primaryPerformance = performanceScore(primary);
  const alternativePerformance = performanceScore(alternative);

  return [
    {
      label: "Price",
      primaryValue: `$${primary.price_usd}`,
      alternativeValue: `$${alternative.price_usd}`,
      verdict:
        primary.price_usd <= alternative.price_usd
          ? `${primary.name} frames the safer spend, so only jump if the extra headroom is real.`
          : `${alternative.name} costs less, so the verdict has to justify paying more for ${primary.name}.`,
    },
    {
      label: "Performance",
      primaryValue: `${readSpecValue(primary, "Memory")} / ${readSpecValue(primary, "Storage")}`,
      alternativeValue: `${readSpecValue(alternative, "Memory")} / ${readSpecValue(alternative, "Storage")}`,
      verdict:
        primaryPerformance >= alternativePerformance
          ? `${primary.name} already has enough performance headroom for this brief without chasing excess.`
          : `${alternative.name} has more raw headroom, but only matters if heavier workloads are real.`,
    },
    {
      label: "Battery",
      primaryValue: primaryBattery,
      alternativeValue: alternativeBattery,
      verdict:
        primaryBatteryValue == null || alternativeBatteryValue == null
          ? "Battery data is incomplete here, so do not let this row make the decision by itself."
          : primaryBatteryValue >= alternativeBatteryValue
            ? `${primary.name} is the safer all-day battery pick.`
            : `${alternative.name} lasts longer, so battery-first buyers may push against the current verdict.`,
    },
    {
      label: "Portability",
      primaryValue: primaryWeight,
      alternativeValue: alternativeWeight,
      verdict:
        primaryWeightValue == null || alternativeWeightValue == null
          ? "Portability data is incomplete here, so keep this row as a secondary check."
          : primaryWeightValue <= alternativeWeightValue
            ? `${primary.name} keeps the mobility penalty lower.`
            : `${alternative.name} travels more easily, so the verdict must lean on other strengths.`,
    },
    {
      label: "Risk",
      primaryValue: "Safer balanced choice",
      alternativeValue: "More specialized bet",
      verdict: `Choose the option that leaves fewer regrets: ${primary.name} is safer, ${alternative.name} is sharper but easier to outgrow or overbuy.`,
    },
  ];
}

export function buildDecisionMemo(
  verdict: PrimaryVerdict,
  alternative: ProductCardBlock | null,
): DecisionMemo {
  const winnerName = verdict.winner?.name ?? null;

  return {
    recommendation: winnerName
      ? `Choose ${winnerName}. It is the clearest fit for the brief right now.`
      : "No current recommendation is ready yet. Load candidates before making the final call.",
    buyIf: winnerName
      ? "Buy this if you want the safest overall fit instead of over-optimizing one dimension."
      : "Buy only after the shortlist has produced a credible winner.",
    avoidIf: verdict.notIdealFor,
    tradeOff: verdict.mainTradeoff,
    revisitWhen: alternative
      ? `Revisit ${alternative.name} if budget pressure rises or raw performance becomes the top priority.`
      : "If your top priority changes sharply, revisit the alternative lane before buying.",
  };
}
