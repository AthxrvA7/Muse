import { AnimatePresence, motion } from "framer-motion";
import { Moon, Sun } from "lucide-react";

import { useTheme } from "@/state/theme";

export function ThemeToggle() {
  const [theme, toggle] = useTheme();
  const dark = theme === "dark";
  return (
    <motion.button
      type="button"
      onClick={toggle}
      whileTap={{ scale: 0.85, rotate: -20 }}
      whileHover={{ scale: 1.08 }}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      title={dark ? "Light mode" : "Dark mode"}
      className="relative grid size-10 place-items-center overflow-hidden rounded-full border border-line bg-surface text-ink shadow-soft"
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={theme}
          initial={{ y: 18, opacity: 0, rotate: -90 }}
          animate={{ y: 0, opacity: 1, rotate: 0 }}
          exit={{ y: -18, opacity: 0, rotate: 90 }}
          transition={{ type: "spring", stiffness: 380, damping: 22 }}
        >
          {dark ? <Moon className="size-[18px] text-amber" /> : <Sun className="size-[18px] text-plum" />}
        </motion.span>
      </AnimatePresence>
    </motion.button>
  );
}
