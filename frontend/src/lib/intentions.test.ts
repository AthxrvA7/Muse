import assert from "node:assert/strict";
import { test } from "node:test";

import { familiarityLabel, INTENTIONS, intentionById, MODE_FAMILIARITY } from "./intentions.ts";

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

test("familiarity defaults follow the backend and read as plain words", () => {
  assert.deepEqual(MODE_FAMILIARITY, { comfort: 0.7, focus: 0.6, energy: 0.6, discovery: 0.3 });
  assert.equal(familiarityLabel(1), "Mostly songs you know");
  assert.equal(familiarityLabel(0.5), "Half familiar, half new");
  assert.equal(familiarityLabel(0), "All new to you");
});
