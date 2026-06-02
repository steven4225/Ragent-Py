import assert from "node:assert/strict";
import test from "node:test";

// @ts-ignore Node's stripped-types test runner needs the explicit extension here.
import {
  getWorkbenchTaskById,
  priceBandIdForBounds,
  recommendationLabelForIndex,
  seedFilterFromTask,
  seedUrlForTask,
  seedUrlForTaskV3,
  stageForWorkbenchState,
} from "./workbench-seed.ts";

test("seedFilterFromTask maps work-laptop to laptop and 1000-1500 band", () => {
  const task = getWorkbenchTaskById("work-laptop");
  assert.ok(task);
  assert.deepEqual(seedFilterFromTask(task), {
    category: "laptop",
    priceBandId: "1000-1500",
    brand: null,
    refine: "",
  });
});

test("seedUrlForTask builds a workbench route with the task query param", () => {
  assert.equal(
    seedUrlForTask("compare-phones"),
    "/preview/ecommerce/workbench-v2?task=compare-phones",
  );
});

test("seedUrlForTaskV3 builds a workbench-v3 route with the task query param", () => {
  assert.equal(
    seedUrlForTaskV3("compare-phones"),
    "/preview/ecommerce/workbench-v3?task=compare-phones",
  );
});

test("legacy v2 seed URL remains unchanged", () => {
  assert.equal(
    seedUrlForTask("compare-phones"),
    "/preview/ecommerce/workbench-v2?task=compare-phones",
  );
});

test("priceBandIdForBounds falls back to any when no exact match exists", () => {
  assert.equal(priceBandIdForBounds(undefined, undefined), "any");
  assert.equal(priceBandIdForBounds(1000, 1500), "1000-1500");
  assert.equal(priceBandIdForBounds(1500, undefined), "1500-plus");
});

test("stageForWorkbenchState moves from explore to compare to decide", () => {
  assert.equal(stageForWorkbenchState(0, false, false), "explore");
  assert.equal(stageForWorkbenchState(2, false, false), "compare");
  assert.equal(stageForWorkbenchState(2, true, false), "decide");
  assert.equal(stageForWorkbenchState(1, false, true), "decide");
});

test("recommendationLabelForIndex returns the three primary decision roles", () => {
  assert.equal(recommendationLabelForIndex(0), "Best fit");
  assert.equal(recommendationLabelForIndex(1), "Performance pick");
  assert.equal(recommendationLabelForIndex(2), "Value pick");
  assert.equal(recommendationLabelForIndex(3), null);
});
