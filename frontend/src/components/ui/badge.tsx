import { type VariantProps, cva } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium [&_svg]:size-3.5", {
  variants: {
    variant: {
      lavender: "bg-lavender-soft text-plum",
      sage: "bg-sage-soft text-moss",
      outline: "border border-line text-ink-soft",
      amber: "bg-amber-soft text-amber",
    },
  },
  defaultVariants: { variant: "lavender" },
});

export function Badge({ className, variant, ...props }: ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
