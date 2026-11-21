import type { ComponentProps, ElementType, ReactNode } from "react";
import { useLocation, useNavigation } from "react-router";

import { cn } from "../lib/utils";

/** Kirish animatsiyasi: pastdan yengil chiqib, o'z joyiga tushadi. `delay` (ms) — navbat (stagger) uchun. */
export function FadeIn<T extends ElementType = "div">({
  as, delay = 0, className, children, ...props
}: { as?: T; delay?: number; className?: string; children?: ReactNode } & Omit<ComponentProps<T>, "as" | "className" | "children">) {
  const Comp = (as ?? "div") as ElementType;
  return (
    <Comp className={cn("animate-in-up", className)} style={{ animationDelay: delay ? `${delay}ms` : undefined }} {...props}>
      {children}
    </Comp>
  );
}

/** Ro'yxat qatori/kartasi uchun stagger kechikishi (ms). Uzun ro'yxatlar sekinlashmasin — `max` dan keyin bir xil. */
export function staggerDelay(index: number, step = 45, max = 8): number {
  return Math.min(index, max) * step;
}

/** `style` sifatida tayyor obyekt — `<tr>`/`<li>` kabi joylarga to'g'ridan-to'g'ri qo'yish uchun. */
export function staggerStyle(index: number, step = 45, max = 8): { animationDelay: string } {
  return { animationDelay: `${staggerDelay(index, step, max)}ms` };
}

/** Marshrut almashganda sahifa mazmuni yengil kirib keladi (AppShell/AdminShell `<Outlet/>` ustida). */
export function PageTransition({ children }: { children: ReactNode }) {
  const location = useLocation();
  return (
    <div key={location.pathname} className="animate-in-fade">
      {children}
    </div>
  );
}

/** Yuqori yupqa yuklanish chizig'i — marshrut/ma'lumot yuklanayotganda (react-router navigatsiya holati). */
export function TopLoader() {
  const navigation = useNavigation();
  if (navigation.state === "idle") return null;
  return (
    <div className="pointer-events-none fixed inset-x-0 top-0 z-50 h-0.5 overflow-hidden bg-primary/15" role="progressbar" aria-label="Yuklanmoqda">
      <div className="h-full w-1/3 rounded-r-full bg-primary animate-loader-slide" />
    </div>
  );
}

/** Skelet — ro'yxat/karta yuklanayotganda haqiqiy mazmun o'rnini egallab turadi. */
export function Skeleton({ className, ...props }: ComponentProps<"div">) {
  return <div className={cn("animate-pulse rounded-lg bg-subtle", className)} {...props} />;
}
