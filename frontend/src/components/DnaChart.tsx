import { CartesianGrid, LabelList, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";

import type { MusicDNA } from "@/lib/types";

type Point = { name: string; valence: number; energy: number };

function Tip({ active, payload }: { active?: boolean; payload?: { payload: Point }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-xl bg-ink px-3 py-2 text-xs text-canvas shadow-lift">
      <div className="font-semibold capitalize">{p.name}</div>
      <div>positivity {Math.round(p.valence * 100)}% · energy {Math.round(p.energy * 100)}%</div>
    </div>
  );
}

function Dot({ cx = 0, cy = 0, r, centre = false }: { cx?: number; cy?: number; r: number; centre?: boolean }) {
  return centre ? (
    <g>
      <circle cx={cx} cy={cy} r={r + 6} fill="var(--c-mint-2)" opacity={0.35} />
      <circle cx={cx} cy={cy} r={r} fill="var(--c-mint)" stroke="var(--c-surface)" strokeWidth={2} />
    </g>
  ) : (
    <circle cx={cx} cy={cy} r={r} fill="var(--c-accent-2)" stroke="var(--c-accent)" strokeWidth={1.5} />
  );
}

/** Your genres on the same valence-energy map Muse uses to match music to moods. */
export function DnaChart({ dna }: { dna: MusicDNA }) {
  const genres: Point[] = dna.genres.map((g) => ({ name: g.name, valence: g.valence, energy: g.energy }));
  const centre: Point[] = dna.mood_centre ? [{ name: "you", ...dna.mood_centre }] : [];
  return (
    <div className="h-72 w-full" role="img" aria-label="Your genres plotted by positivity and energy">
      <ResponsiveContainer>
        <ScatterChart margin={{ top: 12, right: 16, bottom: 24, left: 0 }}>
          <CartesianGrid stroke="var(--c-line)" strokeDasharray="4 4" />
          <XAxis type="number" dataKey="valence" domain={[0, 1]} ticks={[0, 0.5, 1]} tick={{ fill: "var(--c-ink-soft)", fontSize: 11 }} label={{ value: "positivity →", position: "insideBottom", offset: -14, fill: "var(--c-ink-soft)", fontSize: 11 }} />
          <YAxis type="number" dataKey="energy" domain={[0, 1]} ticks={[0, 0.5, 1]} tick={{ fill: "var(--c-ink-soft)", fontSize: 11 }} label={{ value: "energy →", angle: -90, position: "insideLeft", offset: 18, fill: "var(--c-ink-soft)", fontSize: 11 }} />
          <ReferenceLine x={0.5} stroke="var(--c-line)" />
          <ReferenceLine y={0.5} stroke="var(--c-line)" />
          <Tooltip content={<Tip />} cursor={false} />
          <Scatter data={genres} fill="var(--c-accent-2)" stroke="var(--c-accent)" shape={<Dot r={7} />}>
            <LabelList dataKey="name" position="right" offset={10} fill="var(--c-ink)" fontSize={11} />
          </Scatter>
          <Scatter data={centre} shape={<Dot r={10} centre />}>
            <LabelList dataKey="name" position="left" offset={16} fill="var(--c-mint)" fontSize={11} fontWeight={700} />
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
