/* eslint-disable react-refresh/only-export-components -- deck helpers live next to their components */
// Building blocks for the presentation deck: the live room map, chip bars and the QR code.

import { motion } from "framer-motion";
import QRCode from "qrcode";
import { type ReactNode, useEffect, useState } from "react";

import { MOOD_EMOJI } from "@/lib/moods";
import { moodHue } from "@/lib/trajectory";

export const INK = "#17120F";
export const CREAM = "#FFF4E6";
export const PALETTE = {
  tangerine: "#E4572E",
  pink: "#FF4FA3",
  violet: "#2B1B5A",
  lime: "#C6F432",
  cobalt: "#2F4BFF",
  sun: "#FFC93C",
  green: "#13875A",
  ink: INK,
  cream: CREAM,
};

export type Point = { valence: number; energy: number; labels: string[] };

/** The room's moods on the positivity x energy map; new dots pop in as phones vote. */
export function RoomMap({
  points,
  average,
  size = 620,
  ink = CREAM,
}: {
  points: Point[];
  average: { valence: number; energy: number } | null;
  size?: number;
  ink?: string;
}) {
  const pad = 34;
  const at = (v: number, e: number) => [pad + v * (size - 2 * pad), pad + (1 - e) * (size - 2 * pad)] as const;
  const corners = [
    { x: 22, y: 30, t: "TENSE & WIRED", a: "start" },
    { x: size - 22, y: 30, t: "BRIGHT & LIVELY", a: "end" },
    { x: 22, y: size - 18, t: "LOW & SLOW", a: "start" },
    { x: size - 22, y: size - 18, t: "CALM & CONTENT", a: "end" },
  ] as const;
  return (
    <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size} role="img" aria-label={`Mood map with ${points.length} moods`}>
      <rect x={1} y={1} width={size - 2} height={size - 2} rx={36} fill={ink} fillOpacity={0.08} stroke={ink} strokeOpacity={0.2} />
      <line x1={size / 2} y1={12} x2={size / 2} y2={size - 12} stroke={ink} strokeOpacity={0.25} strokeDasharray="6 10" strokeWidth={2} />
      <line x1={12} y1={size / 2} x2={size - 12} y2={size / 2} stroke={ink} strokeOpacity={0.25} strokeDasharray="6 10" strokeWidth={2} />
      {corners.map((c) => (
        <text key={c.t} x={c.x} y={c.y} textAnchor={c.a} fill={ink} fillOpacity={0.6} fontSize={15} fontWeight={800} letterSpacing={2}>
          {c.t}
        </text>
      ))}
      {average && (
        <motion.circle
          cx={at(average.valence, average.energy)[0]}
          cy={at(average.valence, average.energy)[1]}
          animate={{ cx: at(average.valence, average.energy)[0], cy: at(average.valence, average.energy)[1], r: [34, 46, 34] }}
          transition={{ r: { duration: 2.4, repeat: Infinity }, cx: { type: "spring" }, cy: { type: "spring" } }}
          fill="none"
          stroke={ink}
          strokeWidth={4}
          strokeDasharray="5 7"
        />
      )}
      {points.map((p, i) => {
        // A tiny, stable jitter so identical votes don't sit exactly on top of each other
        const jx = (((i * 37) % 17) - 8) * 1.6;
        const jy = (((i * 53) % 19) - 9) * 1.6;
        const [x, y] = at(p.valence, p.energy);
        return (
          <motion.circle
            key={i}
            cx={x + jx}
            cy={y + jy}
            initial={{ r: 0, opacity: 0 }}
            animate={{ r: 13, opacity: 0.92 }}
            transition={{ type: "spring", stiffness: 300, damping: 14 }}
            fill={`hsl(${moodHue(p.valence)} 85% 60%)`}
            stroke={INK}
            strokeOpacity={0.35}
            strokeWidth={2}
          />
        );
      })}
    </svg>
  );
}

/** The most-picked mood chips as growing bars. */
export function ChipBars({ chips, max = 6, ink = CREAM }: { chips: { label: string; count: number }[]; max?: number; ink?: string }) {
  const top = chips.slice(0, max);
  const most = top[0]?.count ?? 1;
  const colours = [PALETTE.pink, PALETTE.lime, PALETTE.sun, PALETTE.cobalt, PALETTE.tangerine, PALETTE.green];
  return (
    <ul className="space-y-3">
      {top.map((chip, i) => (
        <motion.li key={chip.label} layout className="flex items-center gap-3" transition={{ type: "spring", stiffness: 260, damping: 24 }}>
          <span className="w-12 text-center text-4xl">{MOOD_EMOJI[chip.label] ?? "•"}</span>
          <div className="flex-1">
            <motion.div
              className="flex h-12 items-center justify-between rounded-full px-5 text-xl font-bold capitalize"
              style={{ background: colours[i % colours.length], color: i === 3 ? CREAM : INK }}
              animate={{ width: `${32 + 68 * (chip.count / most)}%` }}
              transition={{ type: "spring", stiffness: 120, damping: 18 }}
            >
              <span>{chip.label}</span>
              <span>{chip.count}</span>
            </motion.div>
          </div>
        </motion.li>
      ))}
      {top.length === 0 && <li className="text-2xl" style={{ color: ink, opacity: 0.6 }}>Waiting for the first mood…</li>}
    </ul>
  );
}

/** A QR code for a link, drawn on the page (no external service). */
export function Qr({ url, size = 320, dark = INK, light = CREAM }: { url: string; size?: number; dark?: string; light?: string }) {
  const [src, setSrc] = useState<string | null>(null);
  useEffect(() => {
    let live = true;
    QRCode.toDataURL(url, { margin: 1, width: size * 2, errorCorrectionLevel: "M", color: { dark, light } })
      .then((data) => live && setSrc(data))
      .catch(() => live && setSrc(null));
    return () => {
      live = false;
    };
  }, [url, size, dark, light]);
  return src ? (
    <img src={src} width={size} height={size} alt={`QR code for ${url}`} className="rounded-3xl" />
  ) : (
    <div style={{ width: size, height: size, background: light }} className="rounded-3xl" />
  );
}

/** Same rules as the backend (services/rewind.py): where the room's moods sit on average. */
export function roomPersonality(points: Point[]): { name: string; line: string } | null {
  if (!points.length) return null;
  const v = points.reduce((s, p) => s + p.valence, 0) / points.length;
  const e = points.reduce((s, p) => s + p.energy, 0) / points.length;
  const spread = points.reduce((s, p) => s + Math.hypot(p.valence - v, p.energy - e), 0) / points.length;
  if (points.length >= 4 && spread >= 0.24) return { name: "The Shapeshifter", line: "Your moods moved all over the map, and your music moved with them." };
  if (e >= 0.5) return v >= 0.5 ? { name: "The Sunrise Chaser", line: "Bright, bold and always turning it up." } : { name: "The Midnight Engine", line: "Wired, restless and running on big feelings." };
  return v >= 0.5 ? { name: "The Golden Hour Drifter", line: "Warm, easy and in no hurry at all." } : { name: "The Rainy Window Poet", line: "Soft, slow and deep in your feelings." };
}

/** A small pill label used across slides. */
export function Kicker({ children, bg = INK, fg = CREAM }: { children: ReactNode; bg?: string; fg?: string }) {
  return (
    <span className="inline-block w-fit self-start rounded-full px-5 py-2 text-lg font-extrabold uppercase tracking-[0.2em]" style={{ background: bg, color: fg }}>
      {children}
    </span>
  );
}
