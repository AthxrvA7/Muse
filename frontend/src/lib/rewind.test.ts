import assert from "node:assert/strict";
import { test } from "node:test";

import { rewindUrl, stripLayout } from "./rewind.ts";

const all = { days: 30, moods: true, taste: true, learned: true, playlists: true };

test("the Rewind address carries the options and the time zone", () => {
  const url = new URL(rewindUrl({ ...all, moods: false }, "preview", 330), "https://muse.test");
  assert.equal(url.pathname, "/api/v1/me/rewind");
  assert.equal(url.searchParams.get("moods"), "false");
  assert.equal(url.searchParams.get("taste"), "true");
  assert.equal(url.searchParams.get("tz"), "330");
  assert.equal(url.searchParams.get("format"), "preview");
});

test("time zones are kept inside what the API accepts", () => {
  const url = new URL(rewindUrl(all, "pdf", 9999), "https://muse.test");
  assert.equal(url.searchParams.get("tz"), "840");
});

test("preview pages are cut from the strip at the right places", () => {
  // 3 pages of 315 px with 24 px gaps: 3 * 315 + 2 * 24 = 993
  const layout = stripLayout(993, 560, 3, 280);
  assert.equal(layout.width, 157.5);
  assert.equal(layout.offset(2), (2 * 339) / 2);
});
