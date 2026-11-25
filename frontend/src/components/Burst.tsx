import { motion } from "framer-motion";

const COLOURS = ["var(--c-accent)", "var(--c-coral)", "var(--c-mint)", "var(--c-amber)", "var(--c-sky)"];
const NOTES = ["♪", "♫", "♬", "●", "■"];

/** A one-off burst of notes and confetti from the centre (e.g. a playlist was saved). */
export function Burst({ pieces = 26 }: { pieces?: number }) {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-visible" aria-hidden="true">
      {Array.from({ length: pieces }, (_, i) => {
        const angle = (i / pieces) * Math.PI * 2;
        const distance = 90 + (i % 5) * 28;
        return (
          <motion.span
            key={i}
            className="absolute left-1/2 top-1/2 text-sm font-bold"
            style={{ color: COLOURS[i % COLOURS.length] }}
            initial={{ x: 0, y: 0, opacity: 1, scale: 0.4, rotate: 0 }}
            animate={{
              x: Math.cos(angle) * distance,
              y: Math.sin(angle) * distance + 40,
              opacity: 0,
              scale: 1.2,
              rotate: (i % 2 ? 1 : -1) * 220,
            }}
            transition={{ duration: 1.1 + (i % 4) * 0.12, ease: [0.2, 0.7, 0.4, 1] }}
          >
            {NOTES[i % NOTES.length]}
          </motion.span>
        );
      })}
    </div>
  );
}
