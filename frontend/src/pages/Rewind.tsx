import { motion } from "framer-motion";
import { Check, Disc3, FileDown, Loader2, Share2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { LoginPrompt } from "@/components/LoginPrompt";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api/services";
import { stripLayout, type RewindOptions } from "@/lib/rewind";
import { cn } from "@/lib/utils";
import { useApp } from "@/state/AppState";

const PERIODS = [
  { days: 7, label: "Last week" },
  { days: 30, label: "Last month" },
  { days: 90, label: "Last 3 months" },
];

const PARTS: { id: keyof Omit<RewindOptions, "days">; label: string; hint: string; colour: string }[] = [
  { id: "moods", label: "Moods", hint: "mood of the month, personality, journey", colour: "#FF4FA3" },
  { id: "taste", label: "Taste", hint: "top artists and genres, taste × mood match", colour: "#2F4BFF" },
  { id: "learned", label: "What Muse learned", hint: "your 👍 and 👎", colour: "#E4572E" },
  { id: "playlists", label: "Playlists", hint: "what you saved to Spotify", colour: "#13875A" },
];

const SHOWN_HEIGHT = 360;

type Preview = { key: string; url: string; pages: number; width: number; height: number };

function canShareFiles(): boolean {
  try {
    const probe = new File(["x"], "muse.pdf", { type: "application/pdf" });
    return typeof navigator !== "undefined" && !!navigator.canShare?.({ files: [probe] });
  } catch {
    return false;
  }
}

/** Muse Rewind: the listener's moods and music as a colourful PDF to send to friends. */
export default function Rewind() {
  const { user } = useApp();
  const [options, setOptions] = useState<RewindOptions>({ days: 30, moods: true, taste: true, learned: true, playlists: true });
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"pdf" | "share" | null>(null);
  const [shareable] = useState(canShareFiles);
  const current = useRef<string | null>(null);
  const key = JSON.stringify(options);

  useEffect(() => {
    if (!user) return;
    let live = true;
    const timer = setTimeout(async () => {
      try {
        const { blob, pages } = await api.rewind.get(options, "preview");
        const url = URL.createObjectURL(blob);
        const image = new Image();
        image.src = url;
        await image.decode();
        if (!live) return URL.revokeObjectURL(url);
        if (current.current) URL.revokeObjectURL(current.current);
        current.current = url;
        setPreview({ key: JSON.stringify(options), url, pages, width: image.naturalWidth, height: image.naturalHeight });
        setError(null);
      } catch (e) {
        if (live) setError((e as Error).message);
      }
    }, 650); // wait for the listener to stop tapping before painting a new preview
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [user, options]);

  useEffect(() => () => {
    if (current.current) URL.revokeObjectURL(current.current);
  }, []);

  async function download(share: boolean) {
    setBusy(share ? "share" : "pdf");
    try {
      const { blob } = await api.rewind.get(options, "pdf");
      const name = `muse-rewind-${new Date().toISOString().slice(0, 10)}.pdf`;
      const file = new File([blob], name, { type: "application/pdf" });
      if (share && navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], title: "My Muse Rewind", text: "My moods and music, wrapped by Muse" });
        return;
      }
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = name;
      link.click();
      setTimeout(() => URL.revokeObjectURL(link.href), 10_000);
      toast.success("Your Rewind is downloading", { description: "Send it to your friends!" });
    } catch (e) {
      if ((e as Error).name !== "AbortError") toast.error("Couldn't make your Rewind", { description: (e as Error).message });
    } finally {
      setBusy(null);
    }
  }

  if (!user) {
    return (
      <LoginPrompt title="Log in to make your Muse Rewind">
        Your Rewind is made from your own moods, Music DNA, 👍/👎 and playlists, so it needs your Muse account.
      </LoginPrompt>
    );
  }

  const nothing = !options.moods && !options.taste && !options.learned && !options.playlists;
  const layout = preview ? stripLayout(preview.width, preview.height, preview.pages, SHOWN_HEIGHT) : null;
  const stale = !preview || preview.key !== key;

  return (
    <div className="space-y-6">
      <motion.section
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-[2rem] p-7 text-[#FFF4E6] shadow-lift sm:p-10"
        style={{ background: "linear-gradient(125deg, #2B1B5A 0%, #7a2a8c 45%, #FF4FA3 75%, #E4572E 100%)" }}
      >
        <motion.div
          aria-hidden
          className="absolute -right-20 -top-20 size-44 rounded-full border-[18px] border-[#17120F]/80 bg-[#17120F] opacity-90 sm:-right-16 sm:-top-16 sm:size-80 sm:opacity-100"
          animate={{ rotate: 360 }}
          transition={{ duration: 14, repeat: Infinity, ease: "linear" }}
        >
          <div className="absolute inset-[30%] rounded-full bg-[#FFC93C]" />
          <div className="absolute inset-[47%] rounded-full bg-[#17120F]" />
          <div className="absolute inset-[12%] rounded-full border border-white/10" />
          <div className="absolute inset-[20%] rounded-full border border-white/10" />
        </motion.div>
        <p className="relative text-xs font-bold uppercase tracking-[0.3em] text-[#FFC93C]">New · made just for you</p>
        <h1 className="relative mt-3 font-display text-5xl leading-none sm:text-7xl">Muse Rewind</h1>
        <p className="relative mt-4 max-w-xl text-lg text-[#FFF4E6]/90">
          Your moods and music, wrapped into a colourful PDF: your mood of the month, your Muse personality, your mood
          journey, your sound, and how well your music matched how you felt. Send it to your friends.
        </p>
        <div className="relative mt-5 flex flex-wrap gap-2 text-xs font-semibold">
          {["Up to 10 pages", "Phone-shaped PDF", "Made fresh, never stored"].map((tag, i) => (
            <motion.span key={tag} initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 + i * 0.08 }}
              className="rounded-full bg-[#FFF4E6]/15 px-3 py-1.5 ring-1 ring-[#FFF4E6]/25 backdrop-blur">
              {tag}
            </motion.span>
          ))}
        </div>
      </motion.section>

      <Card className="space-y-5">
        <div className="flex flex-wrap gap-2">
          {PERIODS.map((p) => (
            <button key={p.days} type="button" aria-pressed={options.days === p.days} onClick={() => setOptions({ ...options, days: p.days })}
              className={cn("rounded-full px-4 py-2 text-sm font-semibold transition", options.days === p.days ? "bg-plum text-on-accent" : "bg-lavender-faint text-ink-soft hover:text-ink")}>
              {p.label}
            </button>
          ))}
        </div>
        <div className="grid gap-2 sm:grid-cols-2">
          {PARTS.map((part) => {
            const on = options[part.id];
            return (
              <motion.button key={part.id} type="button" whileTap={{ scale: 0.97 }} aria-pressed={on}
                onClick={() => setOptions({ ...options, [part.id]: !on })}
                className={cn("flex items-center gap-3 rounded-2xl border p-3 text-left transition", on ? "border-transparent bg-raised shadow-soft" : "border-line opacity-60 hover:opacity-90")}>
                <span className="grid size-9 shrink-0 place-items-center rounded-xl text-white transition" style={{ background: on ? part.colour : "var(--c-line)" }}>
                  {on ? <Check className="size-4" /> : null}
                </span>
                <span>
                  <span className="block text-sm font-semibold">{part.label}</span>
                  <span className="block text-xs text-ink-soft">{part.hint}</span>
                </span>
              </motion.button>
            );
          })}
        </div>
      </Card>

      <section aria-label="Preview" className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-2xl">Preview</h2>
          {preview && <span className="text-sm text-ink-soft">{preview.pages} pages</span>}
        </div>
        <div className="relative -mx-4 overflow-x-auto px-4 pb-4 [scrollbar-width:thin]" style={{ minHeight: SHOWN_HEIGHT + 16 }}>
          {error && !preview ? (
            <Card className="text-sm text-ink-soft">{error}</Card>
          ) : !preview || !layout ? (
            <div className="flex gap-4">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} className="shrink-0 animate-pulse rounded-2xl bg-lavender-faint" style={{ width: SHOWN_HEIGHT * 0.5625, height: SHOWN_HEIGHT }} />
              ))}
            </div>
          ) : (
            <div className={cn("flex gap-4 transition-opacity", stale && "opacity-50")}>
              {Array.from({ length: preview.pages }, (_, i) => (
                <motion.div
                  key={`${preview.key}-${i}`}
                  initial={{ opacity: 0, y: 16, rotate: i % 2 ? 1.5 : -1.5 }}
                  animate={{ opacity: 1, y: 0, rotate: 0 }}
                  whileHover={{ y: -8, rotate: i % 2 ? 1.5 : -1.5, scale: 1.02 }}
                  transition={{ delay: Math.min(i * 0.05, 0.4), type: "spring", stiffness: 260, damping: 20 }}
                  className="relative shrink-0 overflow-hidden rounded-2xl shadow-lift"
                  style={{ width: layout.width, height: SHOWN_HEIGHT }}
                >
                  <img src={preview.url} alt={`Rewind page ${i + 1} of ${preview.pages}`} draggable={false}
                    className="absolute left-0 top-0 max-w-none select-none" style={{ height: SHOWN_HEIGHT, width: layout.stripWidth, transform: `translateX(-${layout.offset(i)}px)` }} />
                </motion.div>
              ))}
            </div>
          )}
          {stale && preview && (
            <div className="pointer-events-none absolute inset-0 grid place-items-center">
              <span className="inline-flex items-center gap-2 rounded-full bg-surface px-4 py-2 text-sm font-semibold shadow-lift">
                <Disc3 className="size-4 animate-spin text-plum" /> Repainting…
              </span>
            </div>
          )}
        </div>
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <Button size="lg" onClick={() => download(false)} disabled={busy !== null || nothing}>
          {busy === "pdf" ? <Loader2 className="animate-spin" /> : <FileDown />} Download PDF
        </Button>
        {shareable && (
          <Button size="lg" variant="outline" onClick={() => download(true)} disabled={busy !== null || nothing}>
            {busy === "share" ? <Loader2 className="animate-spin" /> : <Share2 />} Send to friends
          </Button>
        )}
        <p className="text-xs text-ink-soft">
          {nothing ? "Pick at least one part to include." : "Muse paints it on the spot and keeps no copy. Moods appear when your mood trajectory is on (History page)."}
        </p>
      </div>
    </div>
  );
}
