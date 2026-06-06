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
  lane: "更省预算" | "更强性能";
  block: ProductCardBlock | null;
  why: string;
};

export type CompareHighlightRow = {
  label: "价格" | "性能" | "续航" | "便携性" | "风险";
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
    buyingTask: "首轮导购式收敛",
    priorityLine: lower.includes("under $")
      ? "预算 > 续航 > 性能"
      : "匹配度 > 取舍清晰度 > 价格",
    advisorPath:
      stage === "compare"
        ? "先解决当前取舍，再给出最终购买意见。"
        : "先给一个明确主推荐，再对比两个可控替代方案。",
    riskNote: lower.includes("gaming")
      ? "这更像均衡型设备需求，不是纯游戏本导向。"
      : "在主推荐成型之前，不要急着重新铺开全量商品池。",
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
      ? `${winner.name} 是当前最能平衡这条需求的答案。`
      : `围绕“${brief}”还没有形成一个可信的当前主推荐。`,
    notIdealFor: "更在意极限性能、而不是日常综合平衡的人。",
    mainTradeoff: "你选择的是更均衡的全能解，而不是把某一个维度推到极致。",
  };
}

export function buildAlternativeLanes(
  blocks: ProductCardBlock[],
  brief: string,
): AlternativeLane[] {
  const fallback = blocks[0] ?? null;
  return [
    {
      lane: "更省预算",
      block: blocks[1] ?? fallback,
      why: `如果“${brief}”这个方向没变，但你更想压低总预算，可以走这条路线。`,
    },
    {
      lane: "更强性能",
      block: blocks[2] ?? fallback,
      why: `如果你愿意为同一类需求换取更高性能余量，可以走这条路线。`,
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
      label: "价格",
      primaryValue: `$${primary.price_usd}`,
      alternativeValue: `$${alternative.price_usd}`,
      verdict:
        primary.price_usd <= alternative.price_usd
          ? `${primary.name} 的花费更稳，只有在额外性能余量确实有价值时，才值得跳到更贵的选项。`
          : `${alternative.name} 更便宜，所以如果要为 ${primary.name} 多花钱，理由必须足够充分。`,
    },
    {
      label: "性能",
      primaryValue: `${readSpecValue(primary, "Memory")} / ${readSpecValue(primary, "Storage")}`,
      alternativeValue: `${readSpecValue(alternative, "Memory")} / ${readSpecValue(alternative, "Storage")}`,
      verdict:
        primaryPerformance >= alternativePerformance
          ? `${primary.name} 对这条需求已经给出了足够的性能余量，不需要为了纸面参数继续上探。`
          : `${alternative.name} 的原始性能更强，但只有在更重的真实负载下，这个优势才成立。`,
    },
    {
      label: "续航",
      primaryValue: primaryBattery,
      alternativeValue: alternativeBattery,
      verdict:
        primaryBatteryValue == null || alternativeBatteryValue == null
          ? "这里的续航数据不完整，不要只靠这一行就下决定。"
          : primaryBatteryValue >= alternativeBatteryValue
            ? `${primary.name} 是更稳妥的全天续航选择。`
            : `${alternative.name} 更耐用，所以如果你把续航放在第一位，就有理由挑战当前结论。`,
    },
    {
      label: "便携性",
      primaryValue: primaryWeight,
      alternativeValue: alternativeWeight,
      verdict:
        primaryWeightValue == null || alternativeWeightValue == null
          ? "这里的便携性数据不完整，把它当成次级核对项更合适。"
          : primaryWeightValue <= alternativeWeightValue
            ? `${primary.name} 在携带成本上更低。`
            : `${alternative.name} 更适合频繁移动场景，所以主推荐必须依赖别的优势来站住。`,
    },
    {
      label: "风险",
      primaryValue: "更稳妥的均衡解",
      alternativeValue: "更偏科的押注",
      verdict: `优先选更不容易后悔的那一个：${primary.name} 更稳，${alternative.name} 更尖锐，但也更容易买过头或很快暴露短板。`,
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
      ? `当前更建议选 ${winnerName}。它是这条需求下最清晰、最站得住的匹配答案。`
      : "当前还没有形成最终建议，先把候选集拉出来再做结论。",
    buyIf: winnerName
      ? "如果你追求整体最稳妥的匹配，而不是为了单一维度过度优化，就买它。"
      : "等候选列表里出现可信主推荐之后，再进入购买动作。",
    avoidIf: verdict.notIdealFor,
    tradeOff: verdict.mainTradeoff,
    revisitWhen: alternative
      ? `如果预算压力突然上来，或者原始性能变成第一优先级，再回头看 ${alternative.name}。`
      : "如果你的最高优先级发生明显变化，购买前再回看替代路线。",
  };
}
