import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "../lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
  {
    variants: {
      tone: {
        neutral: "bg-subtle text-muted",
        ok: "bg-green/12 text-green",
        bad: "bg-red/10 text-red",
        warn: "bg-amber/12 text-amber",
        info: "bg-primary/10 text-primary",
        gold: "bg-gold/12 text-gold",
      },
      // eski "mono" belgilar ham oddiy shriftda (texnik ko'rinish yo'q); faqat raqamlar tekis
      mono: { true: "tabular-nums", false: "" },
    },
    defaultVariants: { tone: "neutral", mono: false },
  },
);

export function Badge({ className, tone, mono, ...props }: ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone, mono }), className)} {...props} />;
}

/** Qonun havolasi chipi (lex.uz): oltin — faqat rasmiy manbalar uchun */
export function CiteChip({ className, children, ...props }: ComponentProps<"a">) {
  return (
    <a
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "inline-flex max-w-full items-center gap-1.5 rounded-full border border-gold/30 bg-gold/8 px-2.5 py-0.5 text-[13px] font-medium text-gold no-underline hover:border-gold/60 hover:bg-gold/12",
        className,
      )}
      {...props}
    >
      <span className="truncate">{children}</span>
    </a>
  );
}
