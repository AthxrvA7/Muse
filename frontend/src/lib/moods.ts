// How each backend mood chip looks in the UI. The chip ids come from GET /mood/options.

export const MOOD_EMOJI: Record<string, string> = {
  angry: "😤", anxious: "😰", bored: "🥱", calm: "🌿", confident: "😎", dreamy: "☁️",
  energetic: "⚡", focused: "🎯", frustrated: "😣", grateful: "🙏", happy: "😊", heartbroken: "💔",
  hyped: "🔥", lonely: "🌙", low: "🌧️", nostalgic: "📼", relaxed: "🛋️", romantic: "💜",
  stressed: "🌀", tired: "😴",
};

/** A soft background tint from where the mood sits: warm/bright for pleasant, cooler for low. */
export function moodTint(valence: number, energy: number): string {
  if (valence >= 0.6 && energy >= 0.6) return "from-amber-50 to-rose-50";
  if (valence >= 0.6) return "from-emerald-50 to-lavender-faint";
  if (energy >= 0.6) return "from-rose-50 to-lavender-soft";
  return "from-sky-50 to-lavender-soft";
}
