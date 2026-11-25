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
