import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center rounded-3xl border border-dashed border-line bg-surface/60 px-6 py-12 text-center">
      <div className="grid size-12 place-items-center rounded-2xl bg-lavender-soft text-plum">
        <Icon className="size-6" />
      </div>
      <h3 className="mt-4 font-display text-xl text-ink">{title}</h3>
      {children && <div className="mt-2 max-w-sm text-sm text-ink-soft">{children}</div>}
    </div>
  );
}
