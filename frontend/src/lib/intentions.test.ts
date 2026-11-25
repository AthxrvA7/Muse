import assert from "node:assert/strict";
import { test } from "node:test";

import { INTENTIONS, intentionById } from "./intentions.ts";

test("every intention maps to a mode the backend supports", () => {
  const modes = new Set(["comfort", "focus", "energy", "discovery"]);
  for (const intention of INTENTIONS) assert.ok(modes.has(intention.mode), intention.id);
});

test("intention ids are unique", () => {
  assert.equal(new Set(INTENTIONS.map((i) => i.id)).size, INTENTIONS.length);
});

test("unknown ids fall back to matching the mood", () => {
  assert.equal(intentionById("nope").id, "match");
  assert.equal(intentionById("focus").mode, "focus");
  assert.equal(intentionById("escape").mode, "discovery");
});
