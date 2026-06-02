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
