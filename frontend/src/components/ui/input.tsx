import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

const field =
  "w-full rounded-2xl border border-line bg-surface px-4 text-sm text-ink placeholder:text-ink-soft/70 transition focus:border-plum-muted focus:outline-none focus:ring-4 focus:ring-lavender-soft";

export function Input({ className, ...props }: ComponentProps<"input">) {
  return <input className={cn(field, "h-11", className)} {...props} />;
}

export function Textarea({ className, ...props }: ComponentProps<"textarea">) {
  return <textarea className={cn(field, "resize-none py-3 leading-relaxed", className)} {...props} />;
}
