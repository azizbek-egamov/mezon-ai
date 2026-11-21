import { cva, type VariantProps } from "class-variance-authority";
import { Slot } from "radix-ui";
import type { ComponentProps } from "react";

import { cn } from "../lib/utils";

// designs/mezon_klassik/DESIGN.md: bitta asosiy (to'q ko'k) tugma; qolganlari — chegarali yoki matnli
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-lg font-medium transition-[color,box-shadow,background,border,transform] duration-150 active:scale-[0.97] disabled:pointer-events-none disabled:opacity-50 disabled:active:scale-100 focus-visible:outline-none focus-visible:shadow-glow [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        // ikkinchi darajali (oldingi "gold" — endi oltin faqat qonun havolalari uchun)
        gold: "border border-line bg-surface text-ink hover:bg-subtle",
        outline: "border border-line bg-surface text-ink hover:bg-subtle",
        ghost: "text-muted hover:text-ink hover:bg-subtle",
        destructive: "border border-red/40 bg-surface text-red hover:bg-red/10",
        success: "bg-green text-white hover:bg-green/90 dark:text-canvas",
        link: "text-primary underline-offset-4 hover:underline px-0 h-auto",
      },
      size: {
        default: "h-10 px-4 text-sm",
        sm: "h-8 px-3 text-[13px]",
        lg: "h-12 px-6 text-[15px]",
        icon: "size-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export function Button({
  className,
  variant,
  size,
  asChild = false,
  ...props
}: ComponentProps<"button"> & VariantProps<typeof buttonVariants> & { asChild?: boolean }) {
  const Comp = asChild ? Slot.Root : "button";
  return <Comp className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
