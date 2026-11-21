import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps, ReactNode } from "react";

import { cn } from "../lib/utils";

// Oq karta, yengil soya; chap rangli chiziq — faqat holat uchun (xavf, ogohlantirish, tasdiqlangan)
const cardVariants = cva("rounded-xl border border-line bg-surface shadow-card", {
  variants: {
    accent: {
      none: "",
      blue: "border-l-[3px] border-l-primary",
      green: "border-l-[3px] border-l-green",
      red: "border-l-[3px] border-l-red",
      amber: "border-l-[3px] border-l-amber",
      gold: "border-l-[3px] border-l-gold",
    },
  },
  defaultVariants: { accent: "none" },
});

export function Card({ className, accent, ...props }: ComponentProps<"div"> & VariantProps<typeof cardVariants>) {
  return <div className={cn(cardVariants({ accent }), className)} {...props} />;
}

export function CardHeader({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("px-6 pt-5 pb-2", className)} {...props} />;
}

export function CardTitle({ className, ...props }: ComponentProps<"h2">) {
  return <h2 className={cn("font-serif text-[17px] font-semibold", className)} {...props} />;
}

export function CardContent({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("px-6 pb-6", className)} {...props} />;
}

/** Kichik bo'lim yorlig'i (oddiy jumla harfida) */
export function SectionLabel({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("mb-2 text-[13px] font-medium text-muted", className)} {...props} />;
}

/** Sahifa sarlavhasi: serif sarlavha + ixtiyoriy izoh va o'ng tomondagi amallar */
export function PageHeader({ title, description, actions, className }: {
  title: string; description?: string; actions?: ReactNode; className?: string;
}) {
  return (
    <div className={cn("mb-8 flex flex-wrap items-end justify-between gap-4", className)}>
      <div className="min-w-0">
        <h1 className="font-serif text-[28px] font-semibold leading-tight text-ink sm:text-[32px]">{title}</h1>
        {description && <p className="mt-2 max-w-2xl text-[15px] text-muted">{description}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
