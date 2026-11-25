import assert from "node:assert/strict";
import { test } from "node:test";

import { errorMessage } from "./api/client.ts";
import {
  duration,
  greeting,
  joinNames,
  percent,
  playlistName,
  playlistTitle,
  splitList,
  totalDuration,
} from "./format.ts";

test("percent clamps and rounds", () => {
  assert.equal(percent(0.848), "85%");
  assert.equal(percent(1.4), "100%");
  assert.equal(percent(-1), "0%");
});

test("durations read naturally", () => {
  assert.equal(duration(233973), "3:54");
  assert.equal(totalDuration([30 * 60000, 40 * 60000]), "1 hr 10 min");
  assert.equal(totalDuration([233973, 61000]), "5 min");
});

test("names join with 'and'", () => {
  assert.equal(joinNames(["tired"]), "tired");
  assert.equal(joinNames(["tired", "low"]), "tired and low");
  assert.equal(joinNames(["a", "b", "c"]), "a, b and c");
});

test("playlist names come from the mood", () => {
  assert.equal(playlistName(["tired", "low"], "comfort"), "Muse: tired and low");
  assert.equal(playlistName([], "focus"), "Muse: focus");
});

test("titles follow the mood map", () => {
  assert.equal(playlistTitle(0.31, 0.2), "A little somewhere to disappear into.");
  assert.equal(playlistTitle(0.8, 0.9), "Turn it up. You've earned it.");
});

test("greeting follows the time of day", () => {
  assert.equal(greeting(8), "Good morning.");
  assert.equal(greeting(14), "Good afternoon.");
  assert.equal(greeting(21), "Good evening.");
  assert.equal(greeting(3), "Still up?");
});

test("splitList trims and de-duplicates", () => {
  assert.deepEqual(splitList(" Prateek Kuhad,arijit  singh, , prateek kuhad "), ["Prateek Kuhad", "arijit singh"]);
});

test("errorMessage understands every error shape the API sends", () => {
  assert.equal(errorMessage(503, { detail: { message: "Spotify is down" } }), "Spotify is down");
  assert.equal(
    errorMessage(422, { detail: [{ loc: ["body", "track_ids"], msg: "too short" }] }),
    "track_ids: too short",
  );
  assert.equal(errorMessage(429, null), "Too many requests. Wait a moment and try again.");
  assert.equal(errorMessage(500, {}), "Muse had a problem. Please try again.");
});
