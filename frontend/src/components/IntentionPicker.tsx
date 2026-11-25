import { motion } from "framer-motion";
import { Brain, Flame, Heart, Leaf, Plane, Smile, Sparkles } from "lucide-react";

import { INTENTIONS, MODE_LABEL } from "@/lib/intentions";
import { cn } from "@/lib/utils";

const ICONS = { match: Heart, better: Smile, relax: Leaf, focus: Brain, energy: Flame, feel: Sparkles, escape: Plane };

export function IntentionPicker({ value, onChange }: { value: string; onChange: (id: string) => void }) {
  return (
    <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4" role="radiogroup" aria-label="What you want the music to do">
      {INTENTIONS.map((intention) => {
        const Icon = ICONS[intention.id as keyof typeof ICONS];
        const on = value === intention.id;
        return (
          <motion.button
            key={intention.id}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => onChange(intention.id)}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.98 }}
            className={cn(
              "flex flex-col items-start gap-2 rounded-2xl border p-4 text-left transition-colors",
              on ? "border-moss/50 bg-sage-soft shadow-soft" : "border-line bg-surface hover:border-sage hover:bg-sage-soft/40",
            )}
          >
            <span className={cn("grid size-8 place-items-center rounded-xl", on ? "bg-moss text-white" : "bg-sage-soft text-moss")}>
              <Icon className="size-4" />
            </span>
            <span className="text-sm font-semibold text-ink">{intention.label}</span>
            <span className="text-xs leading-snug text-ink-soft">{intention.hint}</span>
            <span className="text-[11px] font-medium uppercase tracking-wider text-moss/80">{MODE_LABEL[intention.mode]} mode</span>
          </motion.button>
        );
      })}
    </div>
  );
}
