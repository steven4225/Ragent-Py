import assert from "node:assert/strict";
import test from "node:test";

import type { ProductCardBlock } from "@/lib/contracts/ecommerce-blocks";

// @ts-ignore Node's stripped-types test runner needs the explicit extension here.
import {
  buildAlternativeLanes,
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
