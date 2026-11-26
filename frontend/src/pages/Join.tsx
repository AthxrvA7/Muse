import { AnimatePresence, motion } from "framer-motion";
import { ArrowRight, Loader2, RotateCcw } from "lucide-react";
import { type ReactNode, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";

import { Burst } from "@/components/Burst";
import { Logo } from "@/components/Logo";
import { ApiError } from "@/lib/api/client";
import { api } from "@/lib/api/services";
import { MOOD_EMOJI } from "@/lib/moods";
import { cn } from "@/lib/utils";

const MAX = 3;
const CHIPS = Object.keys(MOOD_EMOJI);
const COLOURS = ["#FF4FA3", "#C6F432", "#FFC93C", "#2F4BFF", "#E4572E", "#13875A"];

/** A random ID this phone keeps, so each person has one vote (and can change it). */
function voterId(): string {
  try {
    const saved = localStorage.getItem("muse.voter");
    if (saved && /^[A-Za-z0-9_-]{8,40}$/.test(saved)) return saved;
    const fresh = `v-${crypto.randomUUID().replaceAll("-", "").slice(0, 20)}`;
    localStorage.setItem("muse.voter", fresh);
    return fresh;
  } catch {
    return `v-${Math.random().toString(36).slice(2, 14)}${Date.now().toString(36)}`;
  }
}

/** Room mode, on a phone: pick up to 3 moods and send them to the big screen. No login. */
export default function Join() {
  const params = useParams();
  const navigate = useNavigate();
  const code = (params.code ?? "").toUpperCase();
  const [typed, setTyped] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [state, setState] = useState<"picking" | "sending" | "sent">("picking");
  const [error, setError] = useState<string | null>(null);
  const [voter] = useState(voterId);

  useEffect(() => {
    document.title = code ? `Muse room ${code}` : "Join a Muse room";
  }, [code]);

  function toggle(chip: string) {
    setError(null);
    setPicked((now) => (now.includes(chip) ? now.filter((c) => c !== chip) : now.length >= MAX ? [...now.slice(1), chip] : [...now, chip]));
  }

  async function send() {
    if (!picked.length || state === "sending") return;
    setState("sending");
    setError(null);
    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        await api.rooms.vote(code, voter, picked);
        setState("sent");
        if (navigator.vibrate) navigator.vibrate(40);
        return;
      } catch (e) {
        const status = e instanceof ApiError ? e.status : 0;
        if (status === 404) {
          setError("That room doesn't exist (or has closed). Check the code on the screen.");
          break;
        }
        if (status === 422 || status === 409) {
          setError((e as Error).message);
          break;
        }
        await new Promise((r) => setTimeout(r, 800 * (attempt + 1))); // busy Wi-Fi: try again
        if (attempt === 2) setError("Couldn't reach Muse. Check your connection and tap send again.");
      }
    }
    setState("picking");
  }

  if (!code) {
    return (
      <Shell>
        <h1 className="font-display text-4xl leading-tight">Join the room</h1>
        <p className="mt-2 text-[#FFF4E6]/80">Type the 4-letter code on the screen.</p>
        <form className="mt-6 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (typed.length === 4) navigate(`/join/${typed}`); }}>
          <input value={typed} onChange={(e) => setTyped(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 4))}
            inputMode="text" autoCapitalize="characters" autoComplete="off" aria-label="Room code" placeholder="ABCD"
            className="w-full rounded-2xl bg-[#FFF4E6] px-5 py-4 text-center font-display text-3xl tracking-[0.4em] text-[#17120F] outline-none ring-4 ring-transparent focus:ring-[#FFC93C]" />
          <button type="submit" disabled={typed.length !== 4} aria-label="Join"
            className="grid w-16 shrink-0 place-items-center rounded-2xl bg-[#FFC93C] text-[#17120F] disabled:opacity-40">
            <ArrowRight />
          </button>
        </form>
      </Shell>
    );
  }

  return (
    <Shell>
      <AnimatePresence mode="wait">
        {state === "sent" ? (
          <motion.div key="sent" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }} className="relative py-10 text-center">
            <Burst pieces={30} />
            <div className="text-7xl">{picked.map((c) => MOOD_EMOJI[c]).join(" ")}</div>
            <h1 className="mt-6 font-display text-4xl">You&apos;re on the map!</h1>
            <p className="mt-3 text-lg text-[#FFF4E6]/85">Look at the big screen 👀</p>
            <button type="button" onClick={() => setState("picking")}
              className="mt-8 inline-flex items-center gap-2 rounded-full bg-[#FFF4E6]/15 px-5 py-3 font-semibold ring-1 ring-[#FFF4E6]/30">
              <RotateCcw className="size-4" /> Change my mood
            </button>
          </motion.div>
        ) : (
          <motion.div key="pick" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <p className="text-sm font-bold uppercase tracking-[0.25em] text-[#FFC93C]">Room {code}</p>
            <h1 className="mt-2 font-display text-4xl leading-tight">How are you feeling right now?</h1>
            <p className="mt-2 text-[#FFF4E6]/80">Pick up to {MAX}. Only these words go to the screen, no names.</p>
            <div className="mt-6 grid grid-cols-2 gap-2.5">
              {CHIPS.map((chip, i) => {
                const on = picked.includes(chip);
                return (
                  <motion.button key={chip} type="button" whileTap={{ scale: 0.94 }} onClick={() => toggle(chip)} aria-pressed={on}
                    className={cn("flex items-center gap-2 rounded-2xl px-4 py-3.5 text-left text-base font-semibold capitalize transition",
                      on ? "text-[#17120F] shadow-lg" : "bg-[#FFF4E6]/10 text-[#FFF4E6] ring-1 ring-[#FFF4E6]/15")}
                    style={on ? { background: COLOURS[i % COLOURS.length] } : undefined}>
                    <span className="text-2xl">{MOOD_EMOJI[chip]}</span> {chip}
                  </motion.button>
                );
              })}
            </div>
            {error && <p role="alert" className="mt-4 rounded-2xl bg-[#FF4FA3]/20 p-3 text-sm">{error}</p>}
            <div className="sticky bottom-4 mt-6">
              <button type="button" onClick={send} disabled={!picked.length || state === "sending"}
                className="flex w-full items-center justify-center gap-2 rounded-2xl bg-[#FFC93C] py-4 text-lg font-bold text-[#17120F] shadow-2xl transition disabled:opacity-50">
                {state === "sending" ? <Loader2 className="animate-spin" /> : null}
                {picked.length ? `Send ${picked.map((c) => MOOD_EMOJI[c]).join(" ")}` : "Pick a mood"}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </Shell>
  );
}

function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh bg-[#2B1B5A] text-[#FFF4E6]" style={{ background: "linear-gradient(160deg, #2B1B5A 0%, #4a1f6e 55%, #7a2a5c 100%)" }}>
      <div className="mx-auto max-w-md px-5 pb-10 pt-6">
        <div className="mb-6 flex items-center gap-2">
          <Logo className="size-9" />
          <span className="font-display text-xl">Muse</span>
        </div>
        {children}
      </div>
    </div>
  );
}
