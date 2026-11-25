import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, ExternalLink, ThumbsDown, ThumbsUp, X } from "lucide-react";
import { useState } from "react";

import { Tooltip } from "@/components/ui/tooltip";
import { duration, percent } from "@/lib/format";
import type { CuratedTrack } from "@/lib/types";
import { cn } from "@/lib/utils";

function FitBar({ label, value, tone }: { label: string; value: number; tone: "plum" | "moss" }) {
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-20 shrink-0 text-ink-soft">{label}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-lavender-faint">
        <div className={cn("h-full rounded-full", tone === "plum" ? "bg-plum-muted" : "bg-sage")} style={{ width: percent(value) }} />
      </div>
      <span className="w-9 text-right tabular-nums text-ink-soft">{percent(value)}</span>
    </div>
  );
}

export function TrackRow({ item, index, onRemove }: { item: CuratedTrack; index: number; onRemove: () => void }) {
  const [open, setOpen] = useState(false);
  const { track } = item;
  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -24, transition: { duration: 0.18 } }}
      transition={{ delay: Math.min(index * 0.03, 0.4) }}
      className="group rounded-2xl border border-transparent bg-surface transition hover:border-line hover:shadow-soft"
    >
      <div className="flex items-center gap-3 p-2.5 sm:gap-4">
        <span className="hidden w-6 text-right text-sm tabular-nums text-ink-soft sm:block">{index + 1}</span>
        {track.image_url ? (
          <img src={track.image_url} alt="" className="size-12 shrink-0 rounded-xl object-cover sm:size-14" loading="lazy" />
        ) : (
          <div className="size-12 shrink-0 rounded-xl bg-gradient-to-br from-lavender to-sage sm:size-14" />
        )}
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="min-w-0 flex-1 text-left"
        >
          <div className="flex items-center gap-2">
            <span className="truncate font-semibold text-ink">{track.name}</span>
            {track.explicit && <span className="rounded bg-ink-soft/20 px-1 text-[10px] font-bold text-ink-soft">E</span>}
          </div>
          <div className="truncate text-sm text-ink-soft">
            {track.artists.map((a) => a.name).join(", ")} · {track.album}
          </div>
          <div className="mt-0.5 line-clamp-1 text-xs text-plum/90 sm:hidden">{item.reason}</div>
        </button>
        <span className="hidden text-sm tabular-nums text-ink-soft md:block">{duration(track.duration_ms)}</span>
        <div className="flex items-center gap-0.5">
          <Tooltip content="Likes and dislikes arrive with Muse's feedback loop (Phase 3).">
            <span className="hidden sm:inline-flex">
              <button type="button" disabled className="rounded-full p-2 text-ink-soft/40" aria-label="Like (coming in Phase 3)">
                <ThumbsUp className="size-4" />
              </button>
              <button type="button" disabled className="rounded-full p-2 text-ink-soft/40" aria-label="Dislike (coming in Phase 3)">
                <ThumbsDown className="size-4" />
              </button>
            </span>
          </Tooltip>
          <Tooltip content="Open in Spotify">
            <a href={track.spotify_url} target="_blank" rel="noreferrer" className="rounded-full p-2 text-ink-soft transition hover:bg-sage-soft hover:text-moss" aria-label={`Open ${track.name} in Spotify`}>
              <ExternalLink className="size-4" />
            </a>
          </Tooltip>
          <Tooltip content="Remove from this playlist">
            <button type="button" onClick={onRemove} className="rounded-full p-2 text-ink-soft transition hover:bg-danger-soft hover:text-danger" aria-label={`Remove ${track.name}`}>
              <X className="size-4" />
            </button>
          </Tooltip>
          <button type="button" onClick={() => setOpen((o) => !o)} className="rounded-full p-2 text-ink-soft transition hover:bg-lavender-faint" aria-label="Why this track">
            <ChevronDown className={cn("size-4 transition-transform", open && "rotate-180")} />
          </button>
        </div>
      </div>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="mx-2.5 mb-3 space-y-2 rounded-2xl bg-lavender-faint p-4 sm:ml-[5.5rem]">
              <p className="text-sm text-ink">
                <span className="font-semibold text-plum">Why Muse picked it: </span>
                {item.reason}
              </p>
              <FitBar label="Mood fit" value={item.mood_fit} tone="plum" />
              <FitBar label="Taste fit" value={item.taste_fit} tone="moss" />
              <FitBar label="Overall" value={item.score} tone="plum" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.li>
  );
}
