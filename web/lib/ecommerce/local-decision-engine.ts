import type {
  EcommerceCompareResponse,
  EcommerceSearchResponse,
  ProductCardBlock,
  SpecCompareBlock,
} from "@/lib/contracts/ecommerce-blocks";

type LocalProduct = {
  product_id: string;
  name: string;
  brand: string;
  category: string;
  price_usd: number;
  summary: string;
  image_url: string;
  screen: string | null;
  chip: string | null;
  ram_gb: number | null;
  storage_gb: number | null;
  battery_wh: number | null;
  weight_g: number;
  release_year: number;
};

type LocalSearchPayload = {
  query: string;
  category: string | null;
  minPrice?: number;
  maxPrice?: number;
  brand?: string | null;
  limit: number;
};

export type ParsedBrief = {
  category: string | null;
  budgetLabel: string;
  useCase: string;
  mustHaves: string[];
  niceToHaves: string[];
  warnings: string[];
};

export type RecommendationRole = "Best Overall" | "Best Value" | "Power Pick";

export type RecommendationRecord = {
  block: ProductCardBlock;
  role: RecommendationRole;
  rationale: string;
  risk: string;
  scores: {
    fit: number;
    performance: number;
    portability: number;
    value: number;
  };
};

const LOCAL_PRODUCTS: LocalProduct[] = [
  {
    product_id: "laptop-macbook-pro-14-m3pro",
    name: 'MacBook Pro 14" (M3 Pro)',
    brand: "Apple",
    category: "laptop",
    price_usd: 1999,
    summary: "14-inch creator laptop with Apple M3 Pro, mini-LED display, and all-day battery.",
    image_url: "/preview/ecommerce/images/macbook-pro-14-m3pro.svg",
    screen: "14.2-inch Liquid Retina XDR",
    chip: "Apple M3 Pro",
    ram_gb: 18,
    storage_gb: 512,
    battery_wh: 70,
    weight_g: 1610,
    release_year: 2023,
  },
  {
    product_id: "laptop-macbook-air-13-m3",
    name: 'MacBook Air 13" (M3)',
    brand: "Apple",
    category: "laptop",
    price_usd: 1099,
    summary: "Fanless 13-inch ultraportable for daily writing, coding, and video calls.",
    image_url: "/preview/ecommerce/images/macbook-air-13-m3.svg",
    screen: "13.6-inch Liquid Retina",
    chip: "Apple M3",
    ram_gb: 8,
    storage_gb: 256,
    battery_wh: 52,
    weight_g: 1240,
    release_year: 2024,
  },
  {
    product_id: "laptop-thinkpad-x1-carbon-g12",
    name: "ThinkPad X1 Carbon Gen 12",
    brand: "Lenovo",
    category: "laptop",
    price_usd: 1849,
    summary: "14-inch business ultrabook with Intel Core Ultra and best-in-class keyboard.",
    image_url: "/preview/ecommerce/images/thinkpad-x1-carbon-g12.svg",
    screen: "14-inch 2.8K OLED",
    chip: "Intel Core Ultra 7 155H",
    ram_gb: 32,
    storage_gb: 1024,
    battery_wh: 57,
    weight_g: 1090,
    release_year: 2024,
  },
  {
    product_id: "laptop-dell-xps-15-2024",
    name: "Dell XPS 15 (2024)",
    brand: "Dell",
    category: "laptop",
    price_usd: 2199,
    summary: "15.6-inch creator laptop with discrete GPU and 4K OLED option.",
    image_url: "/preview/ecommerce/images/dell-xps-15-2024.svg",
    screen: "15.6-inch 3.5K OLED",
    chip: "Intel Core Ultra 7 155H + RTX 4060",
    ram_gb: 32,
    storage_gb: 1024,
    battery_wh: 86,
    weight_g: 1860,
    release_year: 2024,
  },
  {
    product_id: "laptop-legion-slim-5",
    name: "Lenovo Legion Slim 5",
    brand: "Lenovo",
    category: "laptop",
    price_usd: 1299,
    summary: "Mid-range thin gaming laptop with RTX 4060 and 165Hz panel.",
    image_url: "/preview/ecommerce/images/legion-slim-5.svg",
    screen: "16-inch WQXGA 165Hz",
    chip: "AMD Ryzen 7 7840HS + RTX 4060",
    ram_gb: 16,
    storage_gb: 512,
    battery_wh: 80,
    weight_g: 2280,
    release_year: 2024,
  },
  {
    product_id: "laptop-hp-spectre-x360-14",
    name: "HP Spectre x360 14",
    brand: "HP",
    category: "laptop",
    price_usd: 1499,
    summary: "Convertible 14-inch with OLED touch and pen support.",
    image_url: "/preview/ecommerce/images/hp-spectre-x360-14.svg",
    screen: "14-inch 2.8K OLED touch",
    chip: "Intel Core Ultra 7 155H",
    ram_gb: 16,
    storage_gb: 1024,
    battery_wh: 68,
    weight_g: 1440,
    release_year: 2024,
  },
  {
    product_id: "phone-iphone-15-pro",
    name: "iPhone 15 Pro",
    brand: "Apple",
    category: "phone",
    price_usd: 999,
    summary: "6.1-inch titanium-frame flagship with A17 Pro and USB-C.",
    image_url: "/preview/ecommerce/images/iphone-15-pro.svg",
    screen: "6.1-inch Super Retina XDR",
    chip: "Apple A17 Pro",
    ram_gb: 8,
    storage_gb: 128,
    battery_wh: 13,
    weight_g: 187,
    release_year: 2023,
  },
  {
    product_id: "phone-pixel-8-pro",
    name: "Pixel 8 Pro",
    brand: "Google",
    category: "phone",
    price_usd: 999,
    summary: "6.7-inch Tensor G3 flagship with strong computational photography.",
    image_url: "/preview/ecommerce/images/pixel-8-pro.svg",
    screen: "6.7-inch LTPO OLED 120Hz",
    chip: "Google Tensor G3",
    ram_gb: 12,
    storage_gb: 128,
    battery_wh: 19,
    weight_g: 213,
    release_year: 2023,
  },
  {
    product_id: "phone-galaxy-s24-ultra",
    name: "Samsung Galaxy S24 Ultra",
    brand: "Samsung",
    category: "phone",
    price_usd: 1299,
    summary: "6.8-inch S Pen flagship with titanium frame and 200MP camera.",
    image_url: "/preview/ecommerce/images/galaxy-s24-ultra.svg",
    screen: "6.8-inch QHD+ AMOLED 120Hz",
    chip: "Qualcomm Snapdragon 8 Gen 3 for Galaxy",
    ram_gb: 12,
    storage_gb: 256,
    battery_wh: 19,
    weight_g: 232,
    release_year: 2024,
  },
  {
    product_id: "phone-oneplus-12",
    name: "OnePlus 12",
    brand: "OnePlus",
    category: "phone",
    price_usd: 799,
    summary: "6.82-inch Snapdragon 8 Gen 3 with 100W wired charging.",
    image_url: "/preview/ecommerce/images/oneplus-12.svg",
    screen: "6.82-inch LTPO AMOLED 120Hz",
    chip: "Qualcomm Snapdragon 8 Gen 3",
    ram_gb: 12,
    storage_gb: 256,
    battery_wh: 20,
    weight_g: 220,
    release_year: 2024,
  },
  {
    product_id: "tablet-ipad-pro-13-m4",
    name: 'iPad Pro 13" (M4)',
    brand: "Apple",
    category: "tablet",
    price_usd: 1299,
    summary: "13-inch tandem-OLED tablet with M4 and Apple Pencil Pro support.",
    image_url: "/preview/ecommerce/images/ipad-pro-13-m4.svg",
    screen: "13-inch Tandem OLED",
    chip: "Apple M4",
    ram_gb: 8,
    storage_gb: 256,
    battery_wh: 38,
    weight_g: 579,
    release_year: 2024,
  },
  {
    product_id: "tablet-ipad-air-11-m2",
    name: 'iPad Air 11" (M2)',
    brand: "Apple",
    category: "tablet",
    price_usd: 599,
    summary: "Mid-range 11-inch tablet with M2 and Apple Pencil Pro support.",
    image_url: "/preview/ecommerce/images/ipad-air-11-m2.svg",
    screen: "11-inch Liquid Retina",
    chip: "Apple M2",
    ram_gb: 8,
    storage_gb: 128,
    battery_wh: 29,
    weight_g: 462,
    release_year: 2024,
  },
  {
    product_id: "tablet-galaxy-tab-s9-fe",
    name: "Samsung Galaxy Tab S9 FE",
    brand: "Samsung",
    category: "tablet",
    price_usd: 449,
    summary: "10.9-inch Android tablet with included S Pen.",
    image_url: "/preview/ecommerce/images/galaxy-tab-s9-fe.svg",
    screen: "10.9-inch LCD 90Hz",
    chip: "Samsung Exynos 1380",
    ram_gb: 6,
    storage_gb: 128,
    battery_wh: 31,
    weight_g: 524,
    release_year: 2023,
  },
  {
    product_id: "earbuds-airpods-pro-2",
    name: "AirPods Pro 2 (USB-C)",
    brand: "Apple",
    category: "earbuds",
    price_usd: 249,
    summary: "Active-noise-cancelling earbuds with USB-C MagSafe charging case.",
    image_url: "/preview/ecommerce/images/airpods-pro-2.svg",
    screen: null,
    chip: "Apple H2",
    ram_gb: null,
    storage_gb: null,
    battery_wh: 1,
    weight_g: 51,
    release_year: 2023,
  },
  {
    product_id: "earbuds-sony-wf-1000xm5",
    name: "Sony WF-1000XM5",
    brand: "Sony",
    category: "earbuds",
    price_usd: 299,
    summary: "Class-leading noise cancellation with LDAC and 24-hour case battery.",
    image_url: "/preview/ecommerce/images/sony-wf-1000xm5.svg",
    screen: null,
    chip: "Sony V2 + QN2e",
    ram_gb: null,
    storage_gb: null,
    battery_wh: 1,
    weight_g: 39,
    release_year: 2023,
  },
  {
    product_id: "monitor-lg-32un880",
    name: "LG UltraFine 32UN880",
    brand: "LG",
    category: "monitor",
    price_usd: 599,
    summary: "32-inch 4K monitor with ergo-arm stand and 60W USB-C.",
    image_url: "/preview/ecommerce/images/lg-32un880.svg",
    screen: "31.5-inch 4K UHD IPS",
    chip: null,
    ram_gb: null,
    storage_gb: null,
    battery_wh: null,
    weight_g: 9500,
    release_year: 2021,
  },
  {
    product_id: "monitor-dell-u2723qe",
    name: "Dell UltraSharp U2723QE",
    brand: "Dell",
    category: "monitor",
    price_usd: 649,
    summary: "27-inch 4K IPS Black monitor with KVM and 90W USB-C.",
    image_url: "/preview/ecommerce/images/dell-u2723qe.svg",
    screen: "27-inch 4K UHD IPS Black",
    chip: null,
    ram_gb: null,
    storage_gb: null,
    battery_wh: null,
    weight_g: 6700,
    release_year: 2022,
  },
];

const COMPARE_ROWS = [
  { label: "Price", value: (p: LocalProduct) => `$${p.price_usd.toLocaleString("en-US")}` },
  { label: "Display", value: (p: LocalProduct) => p.screen ?? "-" },
  { label: "Chip", value: (p: LocalProduct) => p.chip ?? "-" },
  { label: "Memory", value: (p: LocalProduct) => (p.ram_gb ? `${p.ram_gb} GB` : "-") },
  { label: "Storage", value: (p: LocalProduct) => (p.storage_gb ? `${p.storage_gb} GB` : "-") },
  { label: "Battery", value: (p: LocalProduct) => (p.battery_wh ? `${p.battery_wh} Wh` : "-") },
  { label: "Weight", value: (p: LocalProduct) => `${p.weight_g} g` },
  { label: "Released", value: (p: LocalProduct) => String(p.release_year) },
];

function toBlock(product: LocalProduct): ProductCardBlock {
  const specs = [
    product.screen ? { label: "Display", value: product.screen } : null,
    product.chip ? { label: "Chip", value: product.chip } : null,
    product.ram_gb ? { label: "Memory", value: `${product.ram_gb} GB` } : null,
    product.storage_gb ? { label: "Storage", value: `${product.storage_gb} GB` } : null,
    product.battery_wh ? { label: "Battery", value: `${product.battery_wh} Wh` } : null,
    { label: "Weight", value: `${product.weight_g} g` },
  ].filter((spec): spec is { label: string; value: string } => Boolean(spec));

  return {
    type: "product_card",
    product_id: product.product_id,
    name: product.name,
    brand: product.brand,
    category: product.category,
    price_usd: product.price_usd,
    summary: product.summary,
    image_url: product.image_url,
    release_year: product.release_year,
    specs,
  };
}

function tokenize(value: string): string[] {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .split(" ")
    .filter((token) => token.length > 1);
}

function scoreProduct(product: LocalProduct, query: string): number {
  const haystack = [
    product.name,
    product.brand,
    product.category,
    product.summary,
    product.screen,
    product.chip,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  let score = 0;
  for (const token of tokenize(query)) {
    if (haystack.includes(token)) score += 3;
  }
  if (/under|budget|value|cheap|parents|family/.test(query.toLowerCase())) {
    score += Math.max(0, 4 - product.price_usd / 500);
  }
  if (/pro|creator|design|edit|performance|gaming|code/.test(query.toLowerCase())) {
    score += (product.ram_gb ?? 0) / 8 + (product.chip?.includes("RTX") ? 3 : 0);
  }
  if (/travel|portable|light|flight/.test(query.toLowerCase())) {
    score += Math.max(0, 3 - product.weight_g / 1000) + (product.battery_wh ?? 0) / 30;
  }
  if (/camera|photo/.test(query.toLowerCase()) && product.category === "phone") score += 4;
  if (/monitor|display|oled|screen/.test(query.toLowerCase()) && product.screen) score += 3;
  return score;
}

export function localSearch(payload: LocalSearchPayload): EcommerceSearchResponse {
  const filtered = LOCAL_PRODUCTS.filter((product) => {
    if (payload.category && product.category !== payload.category) return false;
    if (payload.brand && product.brand !== payload.brand) return false;
    if (payload.minPrice != null && product.price_usd < payload.minPrice) return false;
    if (payload.maxPrice != null && product.price_usd > payload.maxPrice) return false;
    return true;
  });
  const ranked = filtered
    .map((product) => ({ product, score: scoreProduct(product, payload.query) }))
    .sort((left, right) => right.score - left.score || left.product.price_usd - right.product.price_usd);

  return {
    source: "ecommerce-catalog-preview",
    query: payload.query,
    total: ranked.length,
    blocks: ranked.slice(0, payload.limit).map(({ product }) => toBlock(product)),
  };
}

function clampScore(value: number): number {
  return Math.max(1, Math.min(10, Math.round(value)));
}

function extractBudget(query: string): string {
  const match = query.match(/\$?(\d{3,4})/);
  if (!match) return "预算弹性";
  return `${match[1]} 美元以内`;
}

export function parseBrief(query: string): ParsedBrief {
  const text = query.toLowerCase();
  const category =
    text.includes("laptop") || text.includes("notebook")
      ? "laptop"
      : text.includes("phone") || text.includes("iphone") || text.includes("pixel")
        ? "phone"
        : text.includes("tablet") || text.includes("ipad")
          ? "tablet"
          : text.includes("earbud") || text.includes("airpod") || text.includes("anc")
            ? "earbuds"
            : text.includes("monitor") || text.includes("display")
              ? "monitor"
              : null;

  const mustHaves = [
    /oled/.test(text) ? "OLED 屏幕" : null,
    /16gb|32gb|ram/.test(text) ? "更高内存" : null,
    /battery|flight|travel/.test(text) ? "续航能力" : null,
    /light|portable/.test(text) ? "便携性" : null,
    /gaming|gpu|performance|creator|edit/.test(text) ? "性能余量" : null,
    /camera/.test(text) ? "相机素质" : null,
    /pen/.test(text) ? "手写笔支持" : null,
  ].filter((value): value is string => Boolean(value));

  const niceToHaves = [
    /touch/.test(text) ? "触控输入" : null,
    /usb-c/.test(text) ? "USB-C 生态" : null,
    /refresh|120hz|165hz/.test(text) ? "高刷新率屏幕" : null,
    /design|color/.test(text) ? "色彩准确性" : null,
  ].filter((value): value is string => Boolean(value));

  const warnings = [
    /cheap|budget/.test(text) && /performance|gaming/.test(text)
      ? "预算和性能诉求可能会互相拉扯。"
      : null,
    /light|portable/.test(text) && /gaming|gpu/.test(text)
      ? "便携性和独显级性能通常需要互相妥协。"
      : null,
  ].filter((value): value is string => Boolean(value));

  let useCase = "一般购买决策";
  if (/code|developer|calls|office|work/.test(text)) useCase = "办公与生产力";
  if (/gaming/.test(text)) useCase = "游戏与高性能需求";
  if (/creator|design|edit|video/.test(text)) useCase = "创作与媒体工作";
  if (/travel|flight/.test(text)) useCase = "出行与便携场景";
  if (/family|parents|casual/.test(text)) useCase = "家庭与轻量使用";
  if (/camera|photo/.test(text)) useCase = "拍照与移动影像";

  return {
    category,
    budgetLabel: extractBudget(query),
    useCase,
    mustHaves,
    niceToHaves,
    warnings,
  };
}

export function buildRecommendationRecords(
  blocks: ProductCardBlock[],
  query: string,
): RecommendationRecord[] {
  const lowered = query.toLowerCase();
  return blocks.slice(0, 3).map((block, index) => {
    const memory = Number(block.specs.find((spec) => spec.label === "Memory")?.value.replace(/[^\d]/g, "") ?? "0");
    const storage = Number(block.specs.find((spec) => spec.label === "Storage")?.value.replace(/[^\d]/g, "") ?? "0");
    const battery = Number(block.specs.find((spec) => spec.label === "Battery")?.value.replace(/[^\d]/g, "") ?? "0");
    const weight = Number(block.specs.find((spec) => spec.label === "Weight")?.value.replace(/[^\d]/g, "") ?? "0");
    const performanceBase = memory / 4 + storage / 512 + (/RTX|M3 Pro|M4|Ultra|Gen 3/.test(block.summary + block.name + block.brand) ? 2 : 0);
    const portabilityBase = weight > 0 ? 14 - weight / 220 : 5;
    const valueBase = 13 - block.price_usd / 180;
    const fitBase = 7 + (index === 0 ? 2 : index === 1 ? 1 : 0) + (lowered.includes(block.brand.toLowerCase()) ? 1 : 0);
    const role: RecommendationRole =
      index === 0 ? "Best Overall" : index === 1 ? "Best Value" : "Power Pick";
    return {
      block,
      role,
      rationale:
        role === "Best Overall"
          ? `${block.name} is the cleanest all-round match for the current brief.`
          : role === "Best Value"
            ? `${block.name} protects budget while still keeping the brief honest.`
            : `${block.name} leans into stronger hardware or a more opinionated trade-off.`,
      risk:
        role === "Best Overall"
          ? "May not dominate any single metric."
          : role === "Best Value"
            ? "Could leave performance or premium features on the table."
            : "Usually asks for more budget, weight, or complexity.",
      scores: {
        fit: clampScore(fitBase + battery / 40),
        performance: clampScore(performanceBase),
        portability: clampScore(portabilityBase),
        value: clampScore(valueBase),
      },
    };
  });
}

export function localCompare(productIds: string[]): EcommerceCompareResponse {
  const selected = productIds
    .slice(0, 4)
    .map((id) => LOCAL_PRODUCTS.find((product) => product.product_id === id))
    .filter((product): product is LocalProduct => Boolean(product));
  const block: SpecCompareBlock = {
    type: "spec_compare",
    columns: selected.map((product) => ({
      product_id: product.product_id,
      name: product.name,
      brand: product.brand,
      category: product.category,
      image_url: product.image_url,
    })),
    rows: COMPARE_ROWS.map((row) => ({
      label: row.label,
      values: selected.map(row.value),
      has_data: selected.some((product) => row.value(product) !== "-"),
    })),
    placeholder: "Select products to compare.",
  };
  return {
    source: "ecommerce-compare-preview",
    requested_ids: productIds,
    resolved_ids: selected.map((product) => product.product_id),
    missing_ids: productIds.filter((id) => !selected.some((product) => product.product_id === id)),
    truncated: productIds.length > 4,
    block,
  };
}

export function localRecommendationText(query: string): string {
  const result = localSearch({ query, category: null, limit: 3 });
  const [best, second, third] = result.blocks;
  if (!best) {
    return "I could not find a strong catalog match. Try relaxing the category or budget first.";
  }
  const lines = [
    `My pick is ${best.name}. It is the cleanest match for the brief because it balances price, category fit, and the strongest visible specs in this catalog.`,
  ];
  if (second) {
    lines.push(`${second.name} is the main alternative if you want a different trade-off, especially around brand, display, or performance.`);
  }
  if (third) {
    lines.push(`${third.name} stays in the comparison set as the fallback/value check, but I would only choose it if its specific strength matters more than the top pick.`);
  }
  lines.push("Next step: put the top two into Compare, then use Memo to turn the spec table into a final recommendation.");
  return lines.join("\n\n");
}
