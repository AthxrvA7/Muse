import { AnimatePresence, motion } from "framer-motion";
import { Brain, Loader2, ThumbsDown, ThumbsUp } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api/services";
import type { Learned } from "@/lib/types";

/** "What Muse learned": the effect of the listener's 👍/👎, with a way to forget it all. */
export function LearnedCard() {
  const [learned, setLearned] = useState<Learned | null>(null);
  const [forgetting, setForgetting] = useState(false);

  useEffect(() => {
    let live = true;
    api.feedback
      .learned()
      .then((value) => live && setLearned(value))
      .catch(() => live && setLearned({ likes: 0, dislikes: 0, liked_artists: [], avoided_artists: [], ratings: {} }));
    return () => {
      live = false;
    };
  }, []);

  async function forget() {
    setForgetting(true);
    try {
      await api.feedback.forget();
      setLearned({ likes: 0, dislikes: 0, liked_artists: [], avoided_artists: [], ratings: {} });
      toast.success("Muse forgot your ratings", { description: "Your next playlists start fresh." });
    } catch (e) {
      toast.error("Couldn't forget your ratings", { description: (e as Error).message });
    } finally {
      setForgetting(false);
    }
  }

  const total = learned ? learned.likes + learned.dislikes : 0;
  return (
    <Card className="space-y-4">
      <div>
        <CardTitle className="flex items-center gap-2"><Brain className="size-4 text-plum" /> What Muse learned</CardTitle>
        <CardDescription>From your 👍 and 👎 on playlists. Every rating nudges the next mix a little.</CardDescription>
      </div>
      {!learned ? (
        <Loader2 className="size-4 animate-spin text-ink-soft" />
      ) : total === 0 ? (
        <p className="text-sm text-ink-soft">No ratings yet. Use 👍 and 👎 on a playlist, and Muse will learn what you like.</p>
      ) : (
        <div className="space-y-3">
          <div className="flex gap-3 text-sm">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-sage-soft px-3 py-1 font-semibold text-moss"><ThumbsUp className="size-3.5" /> {learned.likes}</span>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-danger-soft px-3 py-1 font-semibold text-danger"><ThumbsDown className="size-3.5" /> {learned.dislikes}</span>
          </div>
          {learned.liked_artists.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-ink-soft">More of</p>
              <div className="flex flex-wrap gap-1.5">
                <AnimatePresence>
                  {learned.liked_artists.map((a, i) => (
                    <motion.span
                      key={a.name}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: i * 0.04 }}
                      className="rounded-full bg-sage-soft px-2.5 py-1 text-xs font-medium text-moss"
                    >
                      {a.name} · {a.count}
                    </motion.span>
                  ))}
                </AnimatePresence>
              </div>
            </div>
          )}
          {learned.avoided_artists.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-xs font-semibold uppercase tracking-[0.12em] text-ink-soft">Less of</p>
              <div className="flex flex-wrap gap-1.5">
                {learned.avoided_artists.map((a) => (
                  <span key={a.name} className="rounded-full bg-danger-soft px-2.5 py-1 text-xs font-medium text-danger">
                    {a.name} · {a.count}
                  </span>
                ))}
              </div>
            </div>
          )}
          <Button variant="outline" size="sm" onClick={forget} disabled={forgetting}>
            {forgetting ? <Loader2 className="animate-spin" /> : null} Forget what Muse learned
          </Button>
        </div>
      )}
    </Card>
  );
}
