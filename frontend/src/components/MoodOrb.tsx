import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";

import type { MoodChip } from "@/lib/types";

/**
 * A living picture of the chosen mood. Colour follows positivity (cool blue when low,
 * warm orange when bright), the pulse follows energy. It can be grabbed and flung;
 * it always springs home.
 */
export function MoodOrb({ chips }: { chips: MoodChip[] }) {
  const valence = chips.length ? chips.reduce((s, c) => s + c.valence, 0) / chips.length : 0.55;
  const energy = chips.length ? chips.reduce((s, c) => s + c.energy, 0) / chips.length : 0.45;
  // Low = deep blue, middle = magenta-coral, bright = warm orange (never green)
  const hue = Math.round(230 + valence * 160) % 360;
  const pulse = 3.6 - energy * 2.6; // seconds per breath: calm is slow, hype is quick

  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const stretch = useSpring(useTransform(x, [-120, 0, 120], [1.25, 1, 1.25]), { stiffness: 300, damping: 20 });
  const squash = useSpring(useTransform(y, [-120, 0, 120], [1.2, 1, 1.2]), { stiffness: 300, damping: 20 });

  const words = [valence > 0.6 ? "bright" : valence < 0.4 ? "heavy" : "even", energy > 0.6 ? "charged" : energy < 0.4 ? "still" : "steady"];

  return (
    <div className="relative grid size-56 place-items-center sm:size-64" aria-hidden="true">
      <motion.div
        drag
        dragSnapToOrigin
        dragElastic={0.35}
        dragTransition={{ bounceStiffness: 420, bounceDamping: 14 }}
        whileTap={{ scale: 0.92 }}
        whileHover={{ scale: 1.04 }}
        style={{ x, y, scaleX: stretch, scaleY: squash }}
        className="relative size-40 cursor-grab touch-none active:cursor-grabbing sm:size-48"
      >
        <motion.div
          className="absolute inset-0 rounded-full blur-2xl"
          animate={{ scale: [1, 1.18, 1], opacity: [0.55, 0.85, 0.55] }}
          transition={{ duration: pulse, repeat: Infinity, ease: "easeInOut" }}
          style={{ background: `hsl(${hue} 95% 60%)` }}
        />
        <motion.div
          className="absolute inset-3 rounded-full"
          animate={{
            borderRadius: ["48% 52% 55% 45%", "55% 45% 48% 52%", "45% 55% 52% 48%", "48% 52% 55% 45%"],
            rotate: [0, 40, -20, 0],
          }}
          transition={{ duration: pulse * 2.2, repeat: Infinity, ease: "easeInOut" }}
          style={{
            background: `radial-gradient(circle at 30% 30%, hsl(${hue + 25} 100% 78%), hsl(${hue} 90% 58%) 45%, hsl(${hue - 25} 85% 38%))`,
            boxShadow: `inset -12px -18px 40px hsl(${hue - 30} 80% 25% / 0.55), inset 10px 12px 30px hsl(${hue + 30} 100% 85% / 0.5)`,
          }}
        />
        <div className="absolute inset-0 grid place-items-center text-center">
          <span className="select-none text-xs font-semibold uppercase tracking-[0.18em] text-white/90 drop-shadow">
            {chips.length ? words.join(" · ") : "drag me"}
          </span>
        </div>
      </motion.div>
    </div>
  );
}
