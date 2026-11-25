import { Slot } from "@radix-ui/react-slot";
import { type VariantProps, cva } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-semibold transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0 cursor-pointer",
  {
    variants: {
      variant: {
        primary: "bg-plum text-white shadow-soft hover:bg-[#5f4b95] hover:shadow-lift active:scale-[0.98]",
        spotify: "bg-moss text-white shadow-soft hover:bg-[#476a52] active:scale-[0.98]",
        soft: "bg-lavender-soft text-plum hover:bg-lavender/60",
        outline: "border border-line bg-surface text-ink hover:border-plum-muted hover:bg-lavender-faint",
        ghost: "text-ink-soft hover:bg-lavender-faint hover:text-ink",
        danger: "bg-danger text-white hover:bg-[#9c3b4c]",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-4",
        lg: "h-12 px-6 text-base",
        icon: "size-9",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

type ButtonProps = ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean };

export function Button({ className, variant, size, asChild = false, ...props }: ButtonProps) {
  const Component = asChild ? Slot : "button";
  return <Component className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
