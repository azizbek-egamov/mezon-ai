import { XIcon } from "lucide-react";
import { Dialog as D } from "radix-ui";
import type { ComponentProps } from "react";

import { cn } from "../lib/utils";

export const Dialog = D.Root;
export const DialogTrigger = D.Trigger;
export const DialogClose = D.Close;

export function DialogContent({ className, children, ...props }: ComponentProps<typeof D.Content>) {
  return (
    <D.Portal>
      <D.Overlay className="fixed inset-0 z-50 bg-black/40 data-[state=open]:animate-in-fade" />
      <D.Content
        className={cn(
          "fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[min(860px,94vw)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto",
          "rounded-2xl border border-line bg-surface p-7 shadow-overlay outline-none",
          "data-[state=open]:animate-in-scale",
          className,
        )}
        {...props}
      >
        {children}
        <D.Close className="absolute right-4 top-4 rounded-md p-1.5 text-muted hover:bg-subtle hover:text-ink" aria-label="×">
          <XIcon className="size-4" />
        </D.Close>
      </D.Content>
    </D.Portal>
  );
}

export function DialogTitle({ className, ...props }: ComponentProps<typeof D.Title>) {
  return <D.Title className={cn("font-serif text-xl font-semibold pr-8", className)} {...props} />;
}

export function DialogDescription({ className, ...props }: ComponentProps<typeof D.Description>) {
  return <D.Description className={cn("mt-1.5 text-[15px] text-muted", className)} {...props} />;
}
