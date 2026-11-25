import { Slot } from "@radix-ui/react-slot";
import { type VariantProps, cva } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-semibold transition-all disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0 cursor-pointer",
  {
    variants: {
      variant: {
        primary: "bg-plum text-on-accent shadow-soft hover:-translate-y-0.5 hover:bg-plum-strong hover:shadow-glow active:translate-y-0 active:scale-95",
        spotify: "bg-moss text-on-accent shadow-soft hover:-translate-y-0.5 hover:bg-moss-strong hover:shadow-lift active:translate-y-0 active:scale-95",
        soft: "bg-lavender-soft text-plum hover:bg-lavender/60",
        outline: "border border-line bg-surface text-ink hover:-translate-y-0.5 hover:border-plum-muted hover:bg-lavender-faint active:translate-y-0 active:scale-95",
        ghost: "text-ink-soft hover:bg-lavender-faint hover:text-ink",
        danger: "bg-danger text-white hover:brightness-110",
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
