import type { CuratedTrack } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Playlist artwork: a 2x2 mosaic of album covers, or a soft gradient when there are none. */
export function Artwork({ tracks, className }: { tracks: CuratedTrack[]; className?: string }) {
  const covers = [...new Set(tracks.map((t) => t.track.image_url).filter(Boolean))].slice(0, 4) as string[];
  if (covers.length < 4) {
    return (
      <div
        className={cn(
          "relative overflow-hidden rounded-3xl bg-gradient-to-br from-lavender via-lavender-soft to-sage shadow-lift",
          className,
        )}
      >
        <div className="absolute -right-6 -top-6 size-32 rounded-full bg-plum/25 blur-2xl" />
        <div className="absolute -bottom-8 -left-4 size-28 rounded-full bg-moss/25 blur-2xl" />
        <span className="absolute bottom-3 left-4 font-display text-3xl text-plum/80">Muse</span>
      </div>
    );
  }
  return (
    <div className={cn("grid grid-cols-2 overflow-hidden rounded-3xl shadow-lift", className)}>
      {covers.map((src) => (
        <img key={src} src={src} alt="" className="aspect-square size-full object-cover" />
      ))}
    </div>
  );
}
