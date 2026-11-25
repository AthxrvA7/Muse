import { motion } from "framer-motion";
import { Check } from "lucide-react";

import { MOOD_EMOJI } from "@/lib/moods";
import type { MoodChip } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  chips: MoodChip[];
  selected: string[];
  max: number;
  onToggle: (id: string) => void;
}

export function MoodPicker({ chips, selected, max, onToggle }: Props) {
  const full = selected.length >= max;
  return (
    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 lg:grid-cols-5" role="group" aria-label="How you feel">
      {chips.map((chip) => {
        const on = selected.includes(chip.id);
        return (
          <motion.button
            key={chip.id}
            type="button"
            onClick={() => onToggle(chip.id)}
            aria-pressed={on}
            disabled={!on && full}
            whileHover={{ y: -3, rotate: on ? 0 : -1 }}
            whileTap={{ scale: 0.9, rotate: 2 }}
            animate={on ? { scale: [1, 1.08, 1] } : { scale: 1 }}
            transition={{ type: "spring", stiffness: 500, damping: 18 }}
            className={cn(
              "group relative flex items-center gap-2.5 rounded-2xl border px-3.5 py-3 text-left text-sm font-medium capitalize transition-colors",
              on
                ? "border-plum-muted bg-lavender-soft text-plum shadow-soft"
                : "border-line bg-surface text-ink hover:border-lavender hover:bg-lavender-faint",
              !on && full && "cursor-not-allowed opacity-45",
            )}
          >
            <motion.span
              className="inline-block text-lg leading-none group-hover:animate-[wiggle_0.5s_ease-in-out]"
              animate={on ? { rotate: [0, -18, 14, 0], scale: [1, 1.35, 1] } : {}}
              transition={{ duration: 0.45 }}
              aria-hidden="true"
            >
              {MOOD_EMOJI[chip.id] ?? "🎵"}
            </motion.span>
            {chip.id}
            {on && (
              <motion.span
                layoutId={`check-${chip.id}`}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                className="absolute right-2.5 top-2.5 grid size-4 place-items-center rounded-full bg-plum text-on-accent"
              >
                <Check className="size-3" strokeWidth={3} />
              </motion.span>
            )}
          </motion.button>
        );
      })}
    </div>
  );
}
