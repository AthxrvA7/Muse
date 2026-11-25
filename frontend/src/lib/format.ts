// Small pure helpers (tested in format.test.ts with Node's built-in test runner).

export function percent(value: number): string {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
}

export function duration(ms: number): string {
  const total = Math.round(ms / 1000);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

export function totalDuration(msList: number[]): string {
  const minutes = Math.round(msList.reduce((sum, ms) => sum + ms, 0) / 60000);
  return minutes >= 60 ? `${Math.floor(minutes / 60)} hr ${minutes % 60} min` : `${minutes} min`;
}

export function joinNames(names: string[]): string {
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}

/** "tired" + "low" -> "Muse: tired and low"; falls back to the mode. */
export function playlistName(labels: string[], mode: string): string {
  const picked = labels.slice(0, 3);
  return `Muse: ${picked.length ? joinNames(picked) : mode}`;
}

/** A short evocative title for a playlist, chosen from where the mood sits on the map. */
export function playlistTitle(valence: number, energy: number): string {
  if (energy < 0.35 && valence < 0.45) return "A little somewhere to disappear into.";
  if (energy < 0.35) return "Soft light, slow hours.";
  if (energy >= 0.65 && valence >= 0.55) return "Turn it up. You've earned it.";
  if (energy >= 0.65) return "Something to burn through it.";
  if (valence >= 0.6) return "Warm, bright and easy.";
  return "Steady ground for a strange day.";
}

/** "Good morning" / "Good afternoon" / "Good evening" for a given hour (0-23). */
export function greeting(hour: number): string {
  if (hour < 5) return "Still up?";
  if (hour < 12) return "Good morning.";
  if (hour < 17) return "Good afternoon.";
  return "Good evening.";
}

/** Splits "a, b,  c" into ["a", "b", "c"] without empties or case-insensitive duplicates. */
export function splitList(text: string): string[] {
  const seen = new Set<string>();
  const items: string[] = [];
  for (const raw of text.split(",")) {
    const item = raw.trim().replace(/\s+/g, " ");
    if (item && !seen.has(item.toLowerCase())) {
      seen.add(item.toLowerCase());
      items.push(item);
    }
  }
  return items;
}

export function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}
