import { cn } from "@/lib/utils";

/**
 * Muse's mark: a record whose groove turns into a pulse shaped like an "M".
 * The disc spins slowly when its parent (a `group`) is hovered.
 */
export function Logo({ className = "size-10", spinning = false }: { className?: string; spinning?: boolean }) {
  return (
    <svg viewBox="0 0 40 40" className={cn("shrink-0", className)} aria-hidden="true">
      <defs>
        <linearGradient id="muse-label" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="var(--c-accent)" />
          <stop offset="1" stopColor="var(--c-coral)" />
        </linearGradient>
      </defs>
      <g className={cn("origin-center [transform-box:fill-box]", spinning ? "spin-slow" : "group-hover:spin-slow")}>
        <circle cx="20" cy="20" r="19" fill="#17120f" />
        <circle cx="20" cy="20" r="15.5" fill="none" stroke="#fff" strokeOpacity="0.1" />
        <circle cx="20" cy="20" r="12.5" fill="none" stroke="#fff" strokeOpacity="0.08" />
        <circle cx="20" cy="20" r="9.5" fill="url(#muse-label)" />
        <circle cx="26.5" cy="12" r="1.4" fill="#fff" fillOpacity="0.55" />
      </g>
      <path
        d="M5.5 22h4.2l2.6-7.5 4.2 12 3.5-12.5 3.5 12.5 4.2-12 2.6 7.5h4.2"
        fill="none"
        stroke="#fff7ee"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
