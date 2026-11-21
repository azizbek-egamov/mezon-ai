import { CheckIcon, Loader2Icon } from "lucide-react";
import { Checkbox as C, Tabs as T } from "radix-ui";
import type { ComponentProps } from "react";

import { cn } from "../lib/utils";

export function Checkbox({ className, ...props }: ComponentProps<typeof C.Root>) {
  return (
    <C.Root
      className={cn(
        "peer mt-0.5 grid size-5 shrink-0 place-items-center rounded-md border border-line bg-surface outline-none focus-visible:shadow-glow data-[state=checked]:border-primary data-[state=checked]:bg-primary",
        className,
      )}
      {...props}
    >
      <C.Indicator>
        <CheckIcon className="size-3.5 text-primary-foreground" strokeWidth={3} />
      </C.Indicator>
    </C.Root>
  );
}

export const Tabs = T.Root;

export function TabsList({ className, ...props }: ComponentProps<typeof T.List>) {
  return <T.List className={cn("flex gap-1 overflow-x-auto overflow-y-hidden border-b border-line [scrollbar-width:none]", className)} {...props} />;
}

export function TabsTrigger({ className, ...props }: ComponentProps<typeof T.Trigger>) {
  return (
    <T.Trigger
      className={cn(
        "-mb-px flex items-center gap-1.5 whitespace-nowrap border-b-2 border-transparent px-3 py-2.5 text-sm font-medium text-muted outline-none hover:text-ink data-[state=active]:border-primary data-[state=active]:text-ink",
        className,
      )}
      {...props}
    />
  );
}

export function TabsContent({ className, ...props }: ComponentProps<typeof T.Content>) {
  return <T.Content className={cn("pt-5 outline-none", className)} {...props} />;
}

export function Progress({ value, className, tone = "blue" }: { value: number; className?: string; tone?: "blue" | "red" | "green" }) {
  const bar = { blue: "bg-primary", red: "bg-red", green: "bg-green" }[tone];
  return (
    <div
      className={cn("h-2 overflow-hidden rounded-full bg-subtle", className)}
      role="progressbar"
      aria-valuenow={Math.round(value)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className={cn("h-full transition-[width] duration-500", bar)} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
    </div>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2Icon className={cn("size-4 animate-spin text-muted", className)} />;
}

export function Empty({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("animate-in-fade py-12 text-center text-[15px] text-muted", className)} {...props} />;
}

/** Xato bloki (API xabari) */
export function ErrorNote({ className, ...props }: ComponentProps<"div">) {
  return <div role="alert" className={cn("rounded-lg border border-red/30 bg-red/8 px-4 py-3 text-sm text-red", className)} {...props} />;
}
