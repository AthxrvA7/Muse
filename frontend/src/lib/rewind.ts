// Muse Rewind helpers (tested in rewind.test.ts with Node's built-in test runner).

export interface RewindOptions {
  days: number;
  moods: boolean;
  taste: boolean;
  learned: boolean;
  playlists: boolean;
}

/** The API address for a Rewind, in the listener's own time zone (for "golden hour"). */
export function rewindUrl(options: RewindOptions, format: "pdf" | "preview", offsetMinutes: number): string {
  const params = new URLSearchParams({
    days: String(options.days),
    moods: String(options.moods),
    taste: String(options.taste),
    learned: String(options.learned),
    playlists: String(options.playlists),
    tz: String(Math.max(-720, Math.min(840, Math.round(offsetMinutes)))),
    format,
  });
  return `/api/v1/me/rewind?${params.toString()}`;
}

/** Where each page sits in the preview strip (pages side by side, 24 px apart). */
export function stripLayout(stripWidth: number, stripHeight: number, pages: number, shownHeight: number) {
  const gap = 24;
  const pageWidth = pages > 0 ? (stripWidth + gap) / pages - gap : 0;
  const scale = stripHeight > 0 ? shownHeight / stripHeight : 0;
  return {
    width: pageWidth * scale,
    stripWidth: stripWidth * scale,
    offset: (i: number) => i * (pageWidth + gap) * scale,
  };
}
