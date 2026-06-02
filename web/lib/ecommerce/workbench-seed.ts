export type WorkbenchCategory =
  | "laptop"
  | "phone"
  | "tablet"
  | "earbuds"
  | "monitor"
  | null;

export type WorkbenchTaskTone =
  | "indigo"
  | "emerald"
  | "amber"
  | "rose"
  | "sky"
  | "violet";

export interface WorkbenchTaskEntry {
  id: string;
  title: string;
  subtitle: string;
  category: WorkbenchCategory;
  minPrice?: number;
  maxPrice?: number;
  query: string;
  tone: WorkbenchTaskTone;
}

export interface WorkbenchPriceBand {
  id: string;
  label: string;
  min?: number;
  max?: number;
}

export interface WorkbenchFilterSeed {
  category: WorkbenchCategory;
  priceBandId: string;
  brand: string | null;
  refine: string;
}

export type WorkbenchStage = "explore" | "compare" | "decide";

export const WORKBENCH_PRICE_BANDS: readonly WorkbenchPriceBand[] = [
  { id: "any", label: "Any" },
  { id: "lt500", label: "< $500", max: 500 },
  { id: "500-1000", label: "$500-$1000", min: 500, max: 1000 },
  { id: "1000-1500", label: "$1000-$1500", min: 1000, max: 1500 },
  { id: "1500-plus", label: "$1500+", min: 1500 },
];

export const WORKBENCH_TASKS: readonly WorkbenchTaskEntry[] = [
  {
    id: "work-laptop",
    title: "Work laptop under $1500",
    subtitle: "Reliable everyday machine for code, docs, and calls.",
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
    subtitle: "Easy reading, video calls, and a big screen.",
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
    subtitle: "Side-by-side trade-offs across camera, battery, and price.",
    category: "phone",
    query: "compare flagship phones across camera, battery, and price",
    tone: "violet",
  },
];

export function getWorkbenchTaskById(taskId: string | null | undefined): WorkbenchTaskEntry | null {
  if (!taskId) return null;
  return WORKBENCH_TASKS.find((task) => task.id === taskId) ?? null;
}

export function priceBandIdForBounds(min: number | undefined, max: number | undefined): string {
  const exact = WORKBENCH_PRICE_BANDS.find((band) => band.min === min && band.max === max);
  if (exact) return exact.id;
  if (max != null && max <= 500) return "lt500";
  if (max != null && max <= 1000) return "500-1000";
  if (max != null && max <= 1500) return "1000-1500";
  if (min != null && min >= 1500) return "1500-plus";
  return "any";
}

export function seedFilterFromTask(task: WorkbenchTaskEntry): WorkbenchFilterSeed {
  return {
    category: task.category,
    priceBandId: priceBandIdForBounds(task.minPrice, task.maxPrice),
    brand: null,
    refine: "",
  };
}

export function seedUrlForTask(taskId: string): string {
  return `/preview/ecommerce/workbench-v2?task=${encodeURIComponent(taskId)}`;
}

export function seedUrlForTaskV3(taskId: string): string {
  return `/preview/ecommerce/workbench-v3?task=${encodeURIComponent(taskId)}`;
}

export function stageForWorkbenchState(
  selectedCount: number,
  hasDecisionOutput: boolean,
  hasAdvisorOutput: boolean,
): WorkbenchStage {
  if (hasDecisionOutput || hasAdvisorOutput) return "decide";
  if (selectedCount >= 2) return "compare";
  return "explore";
}

export function recommendationLabelForIndex(index: number): string | null {
  if (index === 0) return "Best fit";
  if (index === 1) return "Performance pick";
  if (index === 2) return "Value pick";
  return null;
}
