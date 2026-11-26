// Mood trajectory helpers (tested in trajectory.test.ts with Node's built-in test runner).
// The server summarises a logged-in listener's moods; visitors get the same summary
// worked out here from the curations saved in this browser.

import type { MoodPoint, MoodTrajectory } from "./types";

const SHIFT = 0.08; // same rule as the backend (app/services/trajectory.py)

function mean(values: number[]): number {
  return values.reduce((sum, v) => sum + v, 0) / values.length;
}

/** The same summary GET /moods/trajectory returns, for points kept in this browser. */
export function summarise(points: MoodPoint[], days: number): MoodTrajectory {
  const sorted = [...points].sort((a, b) => a.at.localeCompare(b.at));
  if (!sorted.length) return { days, points: [], average: null, top_labels: [], brightness: null, energy: null };
  const counts = new Map<string, number>();
  sorted.forEach((p) => p.labels.forEach((l) => counts.set(l, (counts.get(l) ?? 0) + 1)));
  const top_labels = [...counts.entries()]
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 3);
  let brightness: MoodTrajectory["brightness"] = null;
  let energy: MoodTrajectory["energy"] = null;
  if (sorted.length >= 4) {
    const half = Math.floor(sorted.length / 2);
    const older = sorted.slice(0, half);
    const newer = sorted.slice(-half);
    const v = mean(newer.map((p) => p.valence)) - mean(older.map((p) => p.valence));
    const e = mean(newer.map((p) => p.energy)) - mean(older.map((p) => p.energy));
    brightness = v >= SHIFT ? "lighter" : v <= -SHIFT ? "heavier" : "steady";
    energy = e >= SHIFT ? "more energetic" : e <= -SHIFT ? "calmer" : "steady";
  }
  return {
    days,
    points: sorted,
    average: { valence: mean(sorted.map((p) => p.valence)), energy: mean(sorted.map((p) => p.energy)) },
    top_labels,
    brightness,
    energy,
  };
}

export type DayPart = "morning" | "afternoon" | "evening" | "night";

export function dayPart(date: Date): DayPart {
  const h = date.getHours();
  if (h >= 5 && h < 12) return "morning";
  if (h >= 12 && h < 17) return "afternoon";
  if (h >= 17 && h < 22) return "evening";
  return "night";
}

/** "Your evenings run lowest" — only when two parts of the day clearly differ. */
export function dayPartInsight(points: MoodPoint[]): string | null {
  const groups = new Map<DayPart, number[]>();
  points.forEach((p) => {
    const part = dayPart(new Date(p.at));
    groups.set(part, [...(groups.get(part) ?? []), p.valence]);
  });
  const parts = [...groups.entries()].filter(([, values]) => values.length >= 2).map(([part, values]) => ({ part, v: mean(values) }));
  if (parts.length < 2) return null;
  parts.sort((a, b) => a.v - b.v);
  const low = parts[0];
  const high = parts[parts.length - 1];
  if (high.v - low.v < 0.15) return null;
  const plural = (p: DayPart) => (p === "night" ? "nights" : `${p}s`);
  return `${plural(high.part)[0].toUpperCase()}${plural(high.part).slice(1)} are your brightest, ${plural(low.part)} run lowest`;
}

/** The mood's colour: the same hue Muse paints playlist covers with. */
export function moodHue(valence: number): number {
  return Math.round((230 + valence * 160) % 360);
}

/** Where a mood sits on the map, in words. */
export function quadrant(valence: number, energy: number): string {
  if (energy >= 0.5) return valence >= 0.5 ? "bright & lively" : "tense & wired";
  return valence >= 0.5 ? "calm & content" : "low & slow";
}
