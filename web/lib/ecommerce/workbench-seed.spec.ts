import assert from "node:assert/strict";
import test from "node:test";

// @ts-ignore Node's stripped-types test runner needs the explicit extension here.
import { seedUrlForTask, seedUrlForTaskV3 } from "./workbench-seed.ts";

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
