import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, ExternalLink, Loader2, Pause, Play, ThumbsDown, ThumbsUp, X } from "lucide-react";
import { type CSSProperties, useState } from "react";

import { Tooltip } from "@/components/ui/tooltip";
import { duration, percent } from "@/lib/format";
import type { CuratedTrack } from "@/lib/types";
import { cn } from "@/lib/utils";
import { usePreview } from "@/state/PreviewPlayer";

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

function Badges({ item, className }: { item: CuratedTrack; className?: string }) {
  return (
    <span className={cn("items-center gap-1.5", className)}>
      {!!item.bpm && (
        <span
          className="inline-flex shrink-0 items-center gap-1 rounded-full bg-canvas px-2 py-0.5 text-[10px] font-semibold tabular-nums text-ink-soft ring-1 ring-line"
          title={`${Math.round(item.bpm)} beats per minute`}
        >
          <span
            className="beat size-1.5 rounded-full bg-coral"
            style={{ "--beat": `${(60 / item.bpm).toFixed(3)}s` } as CSSProperties}
            aria-hidden="true"
          />
          {Math.round(item.bpm)} BPM{item.tempo ? ` · ${item.tempo}` : ""}
        </span>
      )}
      {item.known !== undefined && (
        <span
          className={cn(
            "shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-[10px] font-semibold",
            item.known ? "bg-sage-soft text-moss" : "bg-lavender-soft text-plum",
          )}
        >
          {item.known ? "You know this" : "New for you"}
        </span>
      )}
    </span>
  );
}

export function TrackRow({
  item,
  index,
  onRemove,
  rating = 0,
  onRate,
}: {
  item: CuratedTrack;
  index: number;
  onRemove: () => void;
  rating?: 1 | -1 | 0;
  onRate?: (value: 1 | -1 | 0) => void;
}) {
  const [open, setOpen] = useState(false);
  const { playingId, loading, progress, toggle } = usePreview();
  const playing = !!item.preview_id && playingId === item.preview_id;
  const { track } = item;
  return (
    <motion.li
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -24, transition: { duration: 0.18 } }}
      transition={{ delay: Math.min(index * 0.03, 0.4) }}
      className="group rounded-2xl border border-transparent bg-surface transition-colors hover:border-plum/30 hover:bg-raised hover:shadow-soft"
    >
      <div className="flex items-center gap-2.5 p-2 sm:gap-4 sm:p-2.5 sm:transition-transform sm:group-hover:translate-x-1">
        <span className="relative hidden h-5 w-6 sm:block">
          <span
            className={cn(
              "absolute inset-0 text-right text-sm tabular-nums text-ink-soft transition group-hover:opacity-0",
              playing && "opacity-0",
            )}
          >
            {index + 1}
          </span>
          <span
            className={cn(
              "absolute inset-0 flex items-end justify-end gap-[2px] opacity-0 transition group-hover:opacity-100",
              playing && "opacity-100",
            )}
            aria-hidden="true"
          >
            {[0, 0.2, 0.1, 0.3].map((delay) => (
              <span
                key={delay}
                className="eq-bar h-4 w-[3px] rounded-full bg-plum"
                style={{ animationDelay: `${delay}s`, animationDuration: playing && item.bpm ? `${(120 / item.bpm).toFixed(2)}s` : undefined }}
              />
            ))}
          </span>
        </span>
        <motion.div whileHover={{ rotate: playing ? 0 : -4, scale: 1.06 }} className="relative shrink-0">
          {track.image_url ? (
            <img
              src={track.image_url}
              alt=""
              className={cn("size-12 rounded-xl object-cover shadow-soft sm:size-14", playing && "ring-2 ring-plum")}
              loading="lazy"
            />
          ) : (
            <div className="size-12 rounded-xl bg-gradient-to-br from-plum to-coral sm:size-14" />
          )}
          {item.preview_id ? (
            <button
              type="button"
              onClick={() =>
                toggle(item.preview_id!, track.name, {
                  artist: track.artists.map((a) => a.name).join(", "),
                  image: track.image_url,
                  bpm: item.bpm,
                })
              }
              aria-label={playing ? `Stop preview of ${track.name}` : `Play a 30-second preview of ${track.name}`}
              title={playing ? "Stop preview" : "Play 30-second preview"}
              className={cn(
                "absolute inset-0 grid place-items-center rounded-xl bg-black/45 text-white transition",
                playing
                  ? "opacity-100"
                  : "opacity-0 group-hover:opacity-100 focus-visible:opacity-100 [@media(hover:none)]:bg-black/25 [@media(hover:none)]:opacity-100",
              )}
            >
              {playing && loading ? (
                <Loader2 className="size-5 animate-spin" />
              ) : playing ? (
                <Pause className="size-5 fill-current" />
              ) : (
                <Play className="size-5 translate-x-px fill-current" />
              )}
              {playing && (
                <span className="absolute inset-x-1.5 bottom-1.5 h-1 overflow-hidden rounded-full bg-white/30">
                  <span className="block h-full rounded-full bg-white transition-[width]" style={{ width: `${progress * 100}%` }} />
                </span>
              )}
            </button>
          ) : null}
        </motion.div>
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          className="min-w-0 flex-1 text-left"
        >
          <div className="flex min-w-0 items-center gap-2">
            <span className="truncate font-semibold text-ink">{track.name}</span>
            {track.explicit && <span className="shrink-0 rounded bg-ink-soft/20 px-1 text-[10px] font-bold text-ink-soft">E</span>}
            <Badges item={item} className="hidden sm:inline-flex" />
          </div>
          <div className="truncate text-sm text-ink-soft">
            {track.artists.map((a) => a.name).join(", ")} · {track.album}
            {item.genre && <span className="capitalize"> · {item.genre}</span>}
          </div>
          <Badges item={item} className="mt-1 flex flex-wrap sm:hidden" />
          <div className="mt-1 line-clamp-2 text-xs leading-snug text-plum/90 sm:hidden">{item.reason}</div>
          <div className="mt-0.5 flex items-center gap-0.5 text-[11px] font-medium text-ink-soft sm:hidden">
            {open ? "Less" : "Why, and more"} <ChevronDown className={cn("size-3 transition-transform", open && "rotate-180")} />
          </div>
        </button>
        <span className="hidden text-sm tabular-nums text-ink-soft md:block">{duration(track.duration_ms)}</span>
        <div className="flex shrink-0 items-center sm:gap-0.5">
          <span className="inline-flex">
            <Tooltip content={onRate ? (rating === 1 ? "Take back your 👍" : "More like this") : "Log in to rate songs"}>
              <motion.button
                type="button"
                disabled={!onRate}
                onClick={() => onRate?.(rating === 1 ? 0 : 1)}
                whileTap={{ scale: 0.75, rotate: -15 }}
                animate={rating === 1 ? { scale: [1, 1.35, 1] } : { scale: 1 }}
                aria-pressed={rating === 1}
                aria-label={`Like ${track.name}`}
                className={cn(
                  "rounded-full p-2.5 transition disabled:text-ink-soft/40 sm:p-2",
                  rating === 1 ? "bg-sage-soft text-moss" : "text-ink-soft hover:bg-sage-soft hover:text-moss",
                )}
              >
                <ThumbsUp className={cn("size-4", rating === 1 && "fill-current")} />
              </motion.button>
            </Tooltip>
            <Tooltip content={onRate ? "Less like this (Muse will avoid it)" : "Log in to rate songs"}>
              <motion.button
                type="button"
                disabled={!onRate}
                onClick={() => onRate?.(-1)}
                whileTap={{ scale: 0.75, rotate: 15 }}
                aria-label={`Dislike ${track.name}`}
                className="rounded-full p-2.5 text-ink-soft transition hover:bg-danger-soft hover:text-danger disabled:text-ink-soft/40 sm:p-2"
              >
                <ThumbsDown className="size-4" />
              </motion.button>
            </Tooltip>
          </span>
          <Tooltip content="Open in Spotify">
            <a href={track.spotify_url} target="_blank" rel="noreferrer" className="hidden rounded-full p-2 text-ink-soft transition hover:bg-sage-soft hover:text-moss sm:inline-flex" aria-label={`Open ${track.name} in Spotify`}>
              <ExternalLink className="size-4" />
            </a>
          </Tooltip>
          <Tooltip content="Remove from this playlist">
            <button type="button" onClick={onRemove} className="hidden rounded-full p-2 text-ink-soft transition hover:bg-danger-soft hover:text-danger sm:inline-flex" aria-label={`Remove ${track.name}`}>
              <X className="size-4" />
            </button>
          </Tooltip>
          <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} className="hidden rounded-full p-2 text-ink-soft transition hover:bg-lavender-faint sm:inline-flex" aria-label={open ? "Hide details" : "Why this track, and more"}>
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
            <div className="mx-2 mb-3 space-y-2 rounded-2xl bg-lavender-faint p-3.5 sm:mx-2.5 sm:ml-[5.5rem] sm:p-4">
              <p className="text-sm text-ink">
                <span className="font-semibold text-plum">Why Muse picked it: </span>
                {item.reason}
              </p>
              {!!item.tags?.length && (
                <div className="flex flex-wrap items-center gap-1 text-xs">
                  <span className="text-ink-soft">Listeners call it</span>
                  {item.tags.map((tag) => (
                    <span key={tag} className="rounded-full bg-surface px-2 py-0.5 font-medium text-plum">{tag}</span>
                  ))}
                </div>
              )}
              <FitBar label="Mood fit" value={item.mood_fit} tone="plum" />
              <FitBar label="Taste fit" value={item.taste_fit} tone="moss" />
              <FitBar label="Overall" value={item.score} tone="plum" />
              <div className="flex flex-wrap gap-2 pt-1 sm:hidden">
                <a href={track.spotify_url} target="_blank" rel="noreferrer" className="inline-flex h-9 items-center gap-1.5 rounded-full bg-surface px-3 text-xs font-semibold text-moss ring-1 ring-line">
                  <ExternalLink className="size-3.5" /> Open in Spotify
                </a>
                <button type="button" onClick={onRemove} className="inline-flex h-9 items-center gap-1.5 rounded-full bg-surface px-3 text-xs font-semibold text-danger ring-1 ring-line">
                  <X className="size-3.5" /> Remove from playlist
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.li>
  );
}
