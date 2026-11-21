import { Link } from "react-router";

import { cn } from "../lib/utils";

/** Logotip (designs/mezon_klassik): to'q ko'k kvadratda oltin serif "M" + "Mezon". `subtitle` — masalan, admin panel uchun. */
export function Logo({ compact = false, subtitle, to = "/", className }: {
  compact?: boolean; subtitle?: string; to?: string; className?: string;
}) {
  return (
    <Link to={to} className={cn("flex items-center gap-2.5", className)}>
      <LogoMark className="size-9" />
      <span className="leading-tight">
        <span className="block font-serif text-[21px] font-semibold text-ink">Mezon</span>
        {!compact && subtitle && <span className="block text-xs text-muted">{subtitle}</span>}
      </span>
    </Link>
  );
}

export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 36 36" className={cn("shrink-0", className)} aria-hidden>
      <rect width="36" height="36" rx="9" fill="#1F3A5F" />
      <text x="18" y="25.5" textAnchor="middle" fontFamily="Lora Variable, Georgia, serif" fontSize="21" fontWeight="600" fill="#E2C77E">
        M
      </text>
    </svg>
  );
}
