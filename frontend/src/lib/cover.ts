import type { CoverRequest } from "@/lib/types";

/** The preview of the cover Muse puts on the saved Spotify playlist. */
export function coverUrl(cover: CoverRequest): string {
  const params = new URLSearchParams({
    valence: cover.valence.toFixed(2),
    energy: cover.energy.toFixed(2),
    title: cover.title.slice(0, 80),
  });
  cover.words.slice(0, 3).forEach((word) => params.append("words", word.slice(0, 20)));
  return `/api/v1/covers?${params.toString()}`;
}
