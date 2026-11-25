// What the listener wants the music to DO, kept separate from how they feel.
// Each intention maps onto one of the four modes the backend actually implements,
// which change how mood and taste are weighed (see ARCHITECTURE: scoring).

import type { Mode } from "./types";

export interface Intention {
  id: string;
  label: string;
  hint: string;
  mode: Mode;
}

export const INTENTIONS: Intention[] = [
  { id: "match", label: "Match my mood", hint: "Music that sits with you where you are", mode: "comfort" },
  { id: "better", label: "Help me feel better", hint: "Gently lift the energy", mode: "energy" },
  { id: "relax", label: "Help me relax", hint: "Familiar, soft and close to your taste", mode: "comfort" },
  { id: "focus", label: "Help me focus", hint: "Steady energy, few distractions", mode: "focus" },
  { id: "energy", label: "Give me energy", hint: "Turn it up", mode: "energy" },
  { id: "feel", label: "Let me feel everything", hint: "Lean into the feeling", mode: "comfort" },
  { id: "escape", label: "Help me escape", hint: "Let the mood lead into new genres", mode: "discovery" },
];

export function intentionById(id: string): Intention {
  return INTENTIONS.find((intention) => intention.id === id) ?? INTENTIONS[0];
}

export const MODE_LABEL: Record<Mode, string> = {
  comfort: "Comfort",
  focus: "Focus",
  energy: "Energy",
  discovery: "Discovery",
};

/** Share of songs the listener already knows, by mode (the same defaults as the backend). */
export const MODE_FAMILIARITY: Record<Mode, number> = {
  comfort: 0.7,
  focus: 0.6,
  energy: 0.6,
  discovery: 0.3,
};

export function familiarityLabel(value: number): string {
  if (value >= 0.8) return "Mostly songs you know";
  if (value >= 0.55) return "Mostly familiar, a few new";
  if (value >= 0.4) return "Half familiar, half new";
  if (value >= 0.2) return "Mostly new, a few you know";
  return "All new to you";
}
