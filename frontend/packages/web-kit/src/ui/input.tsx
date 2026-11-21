import { EyeIcon, EyeOffIcon } from "lucide-react";
import { useState, type ComponentProps, type KeyboardEvent, type PointerEvent } from "react";

import { extractUzPhoneDigits, formatUzPhoneDisplay } from "../lib/phone";
import { cn } from "../lib/utils";

const field =
  "w-full rounded-lg border border-line bg-surface px-3.5 text-[15px] text-ink placeholder:text-muted/70 outline-none transition-[border,box-shadow] focus:border-primary focus:shadow-glow disabled:opacity-50 aria-[invalid=true]:border-red";

export function Input({ className, ...props }: ComponentProps<"input">) {
  return <input className={cn(field, "h-11", className)} {...props} />;
}

type PasswordInputProps = Omit<ComponentProps<"input">, "type"> & {
  revealLabel: string;
};

/** Parol faqat ko'z tugmasi bosib turilgan vaqt ko'rinadi; qo'yib yuborilishi bilan yana yashiriladi. */
export function PasswordInput({ revealLabel, className, disabled, ...props }: PasswordInputProps) {
  const [revealed, setRevealed] = useState(false);
  const show = () => !disabled && setRevealed(true);
  const hide = () => setRevealed(false);
  const pointerDown = (event: PointerEvent<HTMLButtonElement>) => {
    event.preventDefault(); // input fokusi va mobil klaviatura yopilmasin
    show();
  };
  const keyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === " " || event.key === "Enter") {
      event.preventDefault();
      show();
    }
  };
  const keyUp = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === " " || event.key === "Enter") hide();
  };

  return (
    <div className="relative">
      <Input {...props} disabled={disabled} type={revealed ? "text" : "password"} className={cn("pr-11", className)} />
      <button
        type="button"
        disabled={disabled}
        aria-label={revealLabel}
        aria-pressed={revealed}
        title={revealLabel}
        className="absolute inset-y-0 right-0 flex w-11 touch-none select-none items-center justify-center rounded-r-lg text-muted transition-colors hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 disabled:opacity-50"
        onPointerDown={pointerDown}
        onPointerUp={hide}
        onPointerCancel={hide}
        onPointerLeave={hide}
        onBlur={hide}
        onKeyDown={keyDown}
        onKeyUp={keyUp}
        onContextMenu={(event) => event.preventDefault()}
      >
        {revealed ? <EyeIcon className="size-5" aria-hidden /> : <EyeOffIcon className="size-5" aria-hidden />}
      </button>
    </div>
  );
}

type PhoneInputProps = Omit<ComponentProps<"input">, "type" | "inputMode" | "value" | "onChange"> & {
  value: string;
  onChangePhone: (normalized: string, display: string) => void;
};

/** +998 prefiksi doimiy, foydalanuvchi qismi esa XX XXX XX XX ko'rinishida. */
export function PhoneInput({ value, onChangePhone, className, ...props }: PhoneInputProps) {
  const currentDigits = extractUzPhoneDigits(value);
  const display = formatUzPhoneDisplay(currentDigits);

  return (
    <div className={cn(
      "flex h-11 w-full overflow-hidden rounded-lg border border-line bg-surface text-[15px] text-ink transition-[border,box-shadow] focus-within:border-primary focus-within:shadow-glow",
      props["aria-invalid"] && "border-red",
      className,
    )}>
      <span className="flex shrink-0 items-center border-r border-line bg-subtle px-3.5 tabular-nums text-muted" aria-hidden>
        +998
      </span>
      <input
        {...props}
        type="tel"
        inputMode="numeric"
        value={display}
        maxLength={12}
        placeholder={props.placeholder ?? "90 123 45 67"}
        className="min-w-0 flex-1 bg-transparent px-3.5 tabular-nums outline-none placeholder:text-muted/70 disabled:opacity-50"
        onChange={(event) => {
          const text = event.target.value;
          let digits = extractUzPhoneDigits(text);
          // Formatdagi bo'shliqni Backspace bilan o'chirganda oldingi raqam ham o'chsin.
          if (text.length < display.length && digits === currentDigits && digits.length > 0) {
            digits = digits.slice(0, -1);
          }
          const nextDisplay = formatUzPhoneDisplay(digits);
          onChangePhone(digits ? `+998${digits}` : "", nextDisplay);
        }}
      />
    </div>
  );
}

export function Textarea({ className, ...props }: ComponentProps<"textarea">) {
  return <textarea className={cn(field, "py-2.5 min-h-20", className)} {...props} />;
}

import { CustomSelect, type CustomSelectProps } from "./select";

/** Sayt dizayniga moslashtirilgan Select komponenti (NativeSelect bilan 100% mos keladi). */
export function NativeSelect({ className, ...props }: CustomSelectProps) {
  return <CustomSelect className={cn("w-full", className)} {...props} />;
}

export function Label({ className, ...props }: ComponentProps<"label">) {
  return <label className={cn("block text-sm font-medium text-ink mb-1.5", className)} {...props} />;
}

export function FieldError({ messages }: { messages?: string[] }) {
  if (!messages?.length) return null;
  return (
    <div role="alert" className="mt-1.5 text-[13px] text-red">
      {messages.join(" ")}
    </div>
  );
}
