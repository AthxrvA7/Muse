import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Square } from "lucide-react";

import { usePreview } from "@/state/PreviewPlayer";

/**
 * The mini player: while a 30-second preview plays, a small "record" floats at the
 * bottom of every page with the song, a beat-synced equaliser, progress and stop.
 * It sits above the iPhone home bar (safe-area inset).
 */
export function NowPlaying() {
  const { nowPlaying, loading, progress, stop } = usePreview();
  const beat = nowPlaying?.bpm ? `${(60 / nowPlaying.bpm).toFixed(3)}s` : "0.5s";
  return (
    <AnimatePresence>
      {nowPlaying && (
        <motion.div
          key="now-playing"
          role="status"
          aria-live="polite"
          aria-label={`Playing a preview of ${nowPlaying.title}`}
          initial={{ y: 120, opacity: 0, scale: 0.9 }}
          animate={{ y: 0, opacity: 1, scale: 1 }}
          exit={{ y: 120, opacity: 0, scale: 0.9 }}
          transition={{ type: "spring", stiffness: 340, damping: 28 }}
          className="fixed inset-x-3 z-40 mx-auto max-w-md bottom-[calc(env(safe-area-inset-bottom)+0.75rem)]"
        >
          <div className="relative flex items-center gap-3 overflow-hidden rounded-[1.6rem] border border-line bg-surface/85 p-2 pr-3 shadow-lift backdrop-blur-xl">
            {/* the record: album art on a spinning disc */}
            <motion.div
              className="relative grid size-12 shrink-0 place-items-center rounded-full bg-[#17120F] shadow-soft"
              animate={loading ? { rotate: 0 } : { rotate: 360 }}
              transition={loading ? { duration: 0.2 } : { duration: 3.2, repeat: Infinity, ease: "linear" }}
            >
              <span className="absolute inset-1 rounded-full border border-white/10" />
              <span className="absolute inset-2.5 rounded-full border border-white/10" />
              {nowPlaying.image ? (
                <img src={nowPlaying.image} alt="" className="size-6 rounded-full object-cover" />
              ) : (
                <span className="size-6 rounded-full bg-gradient-to-br from-plum to-coral" />
              )}
              <span className="absolute size-1.5 rounded-full bg-[#17120F]" />
            </motion.div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-semibold text-ink">{nowPlaying.title}</div>
              <div className="flex items-center gap-2 text-xs text-ink-soft">
                <span className="flex h-3 items-end gap-[2px]" aria-hidden="true">
                  {[0, 0.15, 0.3, 0.1].map((delay) => (
                    <span
                      key={delay}
                      className="eq-bar h-3 w-[3px] rounded-full bg-plum"
                      style={{ animationDelay: `${delay}s`, animationDuration: beat, animationPlayState: loading ? "paused" : "running" }}
                    />
                  ))}
                </span>
                <span className="truncate">
                  {loading ? "Loading preview…" : nowPlaying.artist ?? "30-second preview"}
                  {!loading && nowPlaying.bpm ? ` · ${Math.round(nowPlaying.bpm)} BPM` : ""}
                </span>
              </div>
            </div>
            <motion.button
              type="button"
              onClick={stop}
              whileTap={{ scale: 0.85 }}
              aria-label="Stop the preview"
              className="grid size-10 shrink-0 place-items-center rounded-full bg-plum text-on-accent shadow-soft transition hover:bg-plum-strong"
            >
              {loading ? <Loader2 className="size-4 animate-spin" /> : <Square className="size-3.5 fill-current" />}
            </motion.button>
            <span className="absolute inset-x-0 bottom-0 h-[3px] bg-line/60" aria-hidden="true">
              <span className="block h-full bg-gradient-to-r from-plum to-coral transition-[width] duration-300" style={{ width: `${progress * 100}%` }} />
            </span>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
