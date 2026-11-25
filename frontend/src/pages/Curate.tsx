import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, Check, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { api } from "@/lib/api/services";
import { intentionById } from "@/lib/intentions";
import type { CuratePreview, MoodRequest } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useApp } from "@/state/AppState";

// These mirror what the backend really does for POST /curate, in order.
const STEPS = [
  { title: "Understanding your mood", message: "Understanding what you're feeling..." },
  { title: "Gathering songs you love", message: "Looking at what you've been playing..." },
  { title: "Finding artists like yours", message: "Finding artists close to your favourites..." },
  { title: "Reading how each song feels", message: "Checking how listeners describe each song..." },
  { title: "Curating your playlist", message: "Balancing familiar and new..." },
];
const STEP_MS = 650;

export default function Curate() {
  const navigate = useNavigate();
  const { draft, setSession } = useApp();
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const started = useRef(-1);

  useEffect(() => {
    if (draft.chips.length === 0 && !draft.text.trim()) {
      navigate("/", { replace: true });
      return;
    }
    if (started.current === attempt) return; // StrictMode runs effects twice in development
    started.current = attempt;

    const mood: MoodRequest = { chips: draft.chips, mode: intentionById(draft.intention).mode };
    if (draft.text.trim()) mood.text = draft.text.trim();

    // The steps advance on a timer, but the last one only finishes when the API has answered
    let current = 0;
    const timer = setInterval(() => {
      current = Math.min(current + 1, STEPS.length - 1);
      setStep(current);
    }, STEP_MS);
    const minimum = new Promise((resolve) => setTimeout(resolve, STEP_MS * (STEPS.length - 1)));

    Promise.all([api.curation.curate(mood, draft.size, { familiarity: draft.familiarity, exclude: draft.exclude }), minimum])
      .then(([preview]) => {
        clearInterval(timer);
        setStep(STEPS.length);
        setSession({
          id: crypto.randomUUID(),
          created_at: new Date().toISOString(),
          request: { chips: draft.chips, text: draft.text, intention: draft.intention, size: draft.size, familiarity: draft.familiarity, exclude: draft.exclude },
          preview: preview as CuratePreview,
        });
        setTimeout(() => navigate("/results"), 350);
      })
      .catch((e: Error) => {
        clearInterval(timer);
        setError(e.message);
      });
    return () => clearInterval(timer);
  }, [attempt, draft, navigate, setSession]);

  return (
    <div className="mx-auto max-w-xl py-6">
      <p className="text-center text-sm font-medium text-plum">Muse is listening</p>
      <AnimatePresence mode="wait">
        <motion.h1
          key={error ? "error" : Math.min(step, STEPS.length - 1)}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          className="mt-2 text-center font-display text-3xl sm:text-4xl"
        >
          {error ? "That didn't work this time." : STEPS[Math.min(step, STEPS.length - 1)].message}
        </motion.h1>
      </AnimatePresence>

      <div className="mx-auto mt-8 h-1.5 w-full overflow-hidden rounded-full bg-lavender-soft" aria-hidden="true">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-plum-muted to-plum"
          animate={{ width: `${(Math.min(step + 1, STEPS.length) / STEPS.length) * 100}%` }}
          transition={{ ease: "easeOut", duration: 0.5 }}
        />
      </div>

      <Card className="mt-8 p-4 sm:p-6">
        <ol className="space-y-1" aria-live="polite">
          {STEPS.map((s, i) => {
            const done = i < step;
            const active = i === step && !error;
            return (
              <li key={s.title} className={cn("flex items-center gap-3 rounded-2xl px-3 py-2.5 transition", active && "bg-lavender-faint")}>
                <span
                  className={cn(
                    "grid size-7 shrink-0 place-items-center rounded-full text-xs font-semibold",
                    done ? "bg-moss text-white" : active ? "bg-plum text-white" : "bg-lavender-faint text-ink-soft",
                  )}
                >
                  {done ? <Check className="size-4" /> : active ? <Loader2 className="size-4 animate-spin" /> : i + 1}
                </span>
                <span className={cn("text-sm", done || active ? "font-semibold text-ink" : "text-ink-soft")}>
                  Step {i + 1}: {s.title}
                </span>
              </li>
            );
          })}
        </ol>
        {error && (
          <div className="mt-4 flex flex-col gap-3 rounded-2xl bg-danger-soft p-4 text-sm text-danger sm:flex-row sm:items-center sm:justify-between">
            <span className="flex items-start gap-2"><AlertCircle className="mt-0.5 size-4 shrink-0" /> {error}</span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => navigate("/")}>Change mood</Button>
              <Button size="sm" onClick={() => { setError(null); setStep(0); setAttempt((a) => a + 1); }}>Try again</Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
