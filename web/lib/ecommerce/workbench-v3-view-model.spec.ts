import assert from "node:assert/strict";
import test from "node:test";

import type { ProductCardBlock } from "@/lib/contracts/ecommerce-blocks";

// @ts-ignore Node's stripped-types test runner needs the explicit extension here.
import {
  buildAlternativeLanes,
  buildCompareHighlights,
  buildDecisionMemo,
  buildIntentInterpretation,
  buildPrimaryVerdict,
} from "./workbench-v3-view-model.ts";

const sampleBlocks: ProductCardBlock[] = [
  {
    type: "product_card",
    product_id: "a",
    name: "Alpha Book",
    brand: "BrandA",
    category: "laptop",
    price_usd: 1299,
    summary: "Balanced coding laptop",
    image_url: "/alpha.svg",
    release_year: 2025,
    specs: [
      { label: "Memory", value: "16GB" },
      { label: "Storage", value: "512GB" },
      { label: "Battery", value: "70Wh" },
      { label: "Weight", value: "1.3kg" },
    ],
  },
  {
    type: "product_card",
    product_id: "b",
    name: "Budget Book",
    brand: "BrandB",
    category: "laptop",
    price_usd: 999,
    summary: "Lower-cost option",
    image_url: "/budget.svg",
    release_year: 2024,
    specs: [
      { label: "Memory", value: "16GB" },
      { label: "Storage", value: "512GB" },
      { label: "Battery", value: "60Wh" },
      { label: "Weight", value: "1.4kg" },
    ],
  },
  {
    type: "product_card",
    product_id: "c",
    name: "Power Book",
    brand: "BrandC",
    category: "laptop",
    price_usd: 1499,
    summary: "Higher-performance option",
    image_url: "/power.svg",
    release_year: 2025,
    specs: [
      { label: "Memory", value: "32GB" },
      { label: "Storage", value: "1024GB" },
      { label: "Battery", value: "58Wh" },
      { label: "Weight", value: "1.9kg" },
    ],
  },
];

test("buildIntentInterpretation turns a brief into advisor-facing intent fields", () => {
  const result = buildIntentInterpretation(
    "laptop under $1500 for coding, calls, and light gaming",
    "explore",
  );

  assert.equal(result.buyingTask, "First-pass guided selection");
  assert.equal(result.priorityLine, "Budget > battery > performance");
  assert.equal(result.advisorPath, "Recommend one winner first, then compare two controlled alternatives.");
  assert.match(result.riskNote, /not a pure gaming laptop/i);
});

test("buildPrimaryVerdict picks the first block as the current winner and exposes the downside", () => {
  const verdict = buildPrimaryVerdict(sampleBlocks, "coding and calls");

  assert.ok(verdict.winner);
  assert.equal(verdict.winner.product_id, "a");
  assert.match(verdict.why, /Alpha Book/);
  assert.match(verdict.why, /coding and calls/);
  assert.ok(verdict.notIdealFor.length > 0);
  assert.ok(verdict.mainTradeoff.length > 0);
});

test("buildAlternativeLanes keeps only a save-money and performance lane", () => {
  const lanes = buildAlternativeLanes(sampleBlocks, "coding and calls");

  assert.equal(lanes.length, 2);
  assert.equal(lanes[0].lane, "Save money");
  assert.equal(lanes[0].block?.product_id, "b");
  assert.equal(lanes[1].lane, "Push performance");
  assert.equal(lanes[1].block?.product_id, "c");
});

test("view-model helpers degrade safely when the product list is empty", () => {
  const verdict = buildPrimaryVerdict([], "coding and calls");
  const lanes = buildAlternativeLanes([], "coding and calls");

  assert.equal(verdict.winner, null);
  assert.match(verdict.why, /coding and calls/);
  assert.equal(lanes.length, 2);
  assert.equal(lanes[0].block, null);
  assert.equal(lanes[1].block, null);
});

test("buildAlternativeLanes falls back to the first product when controlled alternatives are missing", () => {
  const lanes = buildAlternativeLanes(sampleBlocks.slice(0, 1), "coding and calls");

  assert.equal(lanes.length, 2);
  assert.equal(lanes[0].block?.product_id, "a");
  assert.equal(lanes[1].block?.product_id, "a");
});

test("buildCompareHighlights keeps the compare layer focused on verdict-shaping dimensions", () => {
  const rows = buildCompareHighlights(sampleBlocks[0], sampleBlocks[2]);

  assert.deepEqual(
    rows.map((row) => row.label),
    ["Price", "Performance", "Battery", "Portability", "Risk"],
  );
  assert.equal(rows[0].primaryValue, "$1299");
  assert.equal(rows[0].alternativeValue, "$1499");
  assert.match(rows[1].verdict, /headroom|performance/i);
  assert.ok(rows.every((row) => !["Memory", "Storage", "Weight"].includes(row.label)));
});

test("buildCompareHighlights normalizes terabyte storage when framing performance headroom", () => {
  const rows = buildCompareHighlights(sampleBlocks[0], {
    ...sampleBlocks[2],
    specs: sampleBlocks[2].specs.map((spec) =>
      spec.label === "Storage" ? { ...spec, value: "1 TB" } : spec,
    ),
  });

  assert.match(rows[1].alternativeValue, /1 TB/);
  assert.match(rows[1].verdict, /Power Book has more raw headroom/i);
});

test("buildCompareHighlights stays neutral when battery and portability data are incomplete", () => {
  const rows = buildCompareHighlights(sampleBlocks[0], {
    ...sampleBlocks[1],
    specs: sampleBlocks[1].specs.filter(
      (spec) => spec.label !== "Battery" && spec.label !== "Weight",
    ),
  });

  assert.equal(rows[2].alternativeValue, "-");
  assert.equal(rows[3].alternativeValue, "-");
  assert.match(rows[2].verdict, /battery data is incomplete/i);
  assert.match(rows[3].verdict, /portability data is incomplete/i);
});

test("buildDecisionMemo produces a concise rational advisor memo", () => {
  const verdict = buildPrimaryVerdict(sampleBlocks, "coding and calls");
  const memo = buildDecisionMemo(verdict, sampleBlocks[1]);

  assert.match(memo.recommendation, /Alpha Book/);
  assert.match(memo.buyIf, /safest overall fit|balanced/i);
  assert.equal(memo.avoidIf, verdict.notIdealFor);
  assert.equal(memo.tradeOff, verdict.mainTradeoff);
  assert.match(memo.revisitWhen, /Budget Book/);
});

test("buildDecisionMemo stays usable when there is no alternative product", () => {
  const verdict = buildPrimaryVerdict(sampleBlocks, "coding and calls");
  const memo = buildDecisionMemo(verdict, null);

  assert.match(memo.recommendation, /Alpha Book/);
  assert.match(memo.revisitWhen, /alternative lane/i);
});

test("buildDecisionMemo stays readable when there is no current winner yet", () => {
  const verdict = buildPrimaryVerdict([], "coding and calls");
  const memo = buildDecisionMemo(verdict, null);

  assert.match(memo.recommendation, /no current recommendation/i);
  assert.match(memo.buyIf, /shortlist has produced a credible winner/i);
});
