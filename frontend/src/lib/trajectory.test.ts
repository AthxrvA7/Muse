import assert from "node:assert/strict";
import { test } from "node:test";

import { dayPart, dayPartInsight, moodHue, quadrant, summarise } from "./trajectory.ts";
import type { MoodPoint } from "./types.ts";

function point(day: number, valence: number, energy = 0.5, labels = ["calm"], hour = 10): MoodPoint {
  const at = new Date(2026, 10, 1 + day, hour).toISOString();
  return { at, valence, energy, labels, mode: "comfort" };
}

test("no points, no summary", () => {
  const result = summarise([], 30);
  assert.deepEqual(result.points, []);
  assert.equal(result.average, null);
  assert.equal(result.brightness, null);
});

test("averages, top mood words and the oldest-first order", () => {
  const result = summarise([point(2, 0.6), point(0, 0.2, 0.5, ["low"]), point(1, 0.4, 0.5, ["low", "tired"])], 7);
  assert.deepEqual(result.points.map((p) => p.valence), [0.2, 0.4, 0.6]);
  assert.ok(Math.abs((result.average?.valence ?? 0) - 0.4) < 1e-9);
  assert.deepEqual(result.top_labels[0], { label: "low", count: 2 });
  assert.equal(result.brightness, null); // fewer than 4 points
});

test("recent half against the earlier half, like the backend", () => {
  assert.equal(summarise([0.2, 0.3, 0.6, 0.7].map((v, i) => point(i, v)), 30).brightness, "lighter");
  assert.equal(summarise([0.8, 0.7, 0.3, 0.2].map((v, i) => point(i, v)), 30).brightness, "heavier");
  assert.equal(summarise([0.9, 0.8, 0.4, 0.3, 0.2].map((e, i) => point(i, 0.5, e)), 30).energy, "calmer");
});

test("parts of the day and the insight about them", () => {
  assert.equal(dayPart(new Date(2026, 0, 1, 8)), "morning");
  assert.equal(dayPart(new Date(2026, 0, 1, 23)), "night");
  const mornings = [point(0, 0.8, 0.5, ["happy"], 9), point(1, 0.7, 0.5, ["happy"], 8)];
  const nights = [point(0, 0.2, 0.5, ["low"], 23), point(1, 0.3, 0.5, ["low"], 1)];
  assert.equal(dayPartInsight([...mornings, ...nights]), "Mornings are your brightest, nights run lowest");
  assert.equal(dayPartInsight(mornings), null); // one part of the day only
});

test("colour and words for a place on the mood map", () => {
  assert.equal(moodHue(0), 230);
  assert.equal(moodHue(1), 30);
  assert.equal(quadrant(0.8, 0.8), "bright & lively");
  assert.equal(quadrant(0.2, 0.2), "low & slow");
});
