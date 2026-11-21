import { CheckIcon, ChevronDownIcon, ChevronUpIcon } from "lucide-react";
import { Select as S } from "radix-ui";
import {
  Children,
  isValidElement,
  type ComponentProps,
  type ReactNode,
} from "react";

import { cn } from "../lib/utils";

export const Select = S.Root;
export const SelectGroup = S.Group;
export const SelectValue = S.Value;

export function SelectTrigger({
  className,
  children,
  size = "md",
  ...props
}: ComponentProps<typeof S.Trigger> & { size?: "sm" | "md" }) {
  return (
    <S.Trigger
      className={cn(
        "flex items-center justify-between gap-2 rounded-lg border border-line bg-surface text-ink outline-none transition-[border,box-shadow,background-color]",
        "focus:border-primary focus:shadow-glow disabled:cursor-not-allowed disabled:opacity-50",
        "[&>span]:line-clamp-1 [&[data-placeholder]>span]:text-muted/70",
        size === "sm" ? "h-8 px-2.5 text-[13px] w-auto shrink-0" : "h-11 px-3.5 text-[15px] w-full",
        className,
      )}
      {...props}
    >
      {children}
      <S.Icon asChild>
        <ChevronDownIcon
          className={cn(
            "shrink-0 text-muted transition-transform duration-200 [[data-state=open]>&]:rotate-180",
            size === "sm" ? "size-3.5 ml-1" : "size-4",
          )}
        />
      </S.Icon>
    </S.Trigger>
  );
}

export function SelectContent({
  className,
  children,
  position = "popper",
  ...props
}: ComponentProps<typeof S.Content>) {
  return (
    <S.Portal>
      <S.Content
        position={position}
        sideOffset={4}
        className={cn(
          "relative z-50 max-h-80 min-w-[8rem] overflow-hidden rounded-xl border border-line bg-surface p-1 text-ink shadow-overlay outline-none",
          "data-[state=open]:animate-in-scale",
          position === "popper" &&
            "data-[side=bottom]:translate-y-1 data-[side=left]:-translate-x-1 data-[side=right]:translate-x-1 data-[side=top]:-translate-y-1",
          className,
        )}
        {...props}
      >
        <S.ScrollUpButton className="flex cursor-default items-center justify-center py-1 text-muted">
          <ChevronUpIcon className="size-3.5" />
        </S.ScrollUpButton>
        <S.Viewport
          className={cn(
            "p-0.5",
            position === "popper" && "w-full min-w-[var(--radix-select-trigger-width)]",
          )}
        >
          {children}
        </S.Viewport>
        <S.ScrollDownButton className="flex cursor-default items-center justify-center py-1 text-muted">
          <ChevronDownIcon className="size-3.5" />
        </S.ScrollDownButton>
      </S.Content>
    </S.Portal>
  );
}

export function SelectItem({
  className,
  children,
  size = "md",
  ...props
}: ComponentProps<typeof S.Item> & { size?: "sm" | "md" }) {
  return (
    <S.Item
      className={cn(
        "relative flex w-full cursor-pointer select-none items-center rounded-lg outline-none transition-colors",
        "text-ink hover:bg-subtle focus:bg-subtle focus:text-ink data-[disabled]:pointer-events-none data-[disabled]:opacity-50",
        "data-[state=checked]:bg-primary/10 data-[state=checked]:font-medium data-[state=checked]:text-primary",
        size === "sm" ? "py-1.5 pl-2.5 pr-8 text-[13px]" : "py-2 pl-3 pr-9 text-[14px]",
        className,
      )}
      {...props}
    >
      <S.ItemText>{children}</S.ItemText>
      <span
        className={cn(
          "absolute right-2 flex items-center justify-center",
          size === "sm" ? "size-3.5" : "size-4",
        )}
      >
        <S.ItemIndicator>
          <CheckIcon className={cn("text-primary", size === "sm" ? "size-3.5" : "size-4")} />
        </S.ItemIndicator>
      </span>
    </S.Item>
  );
}

export function SelectLabel({ className, ...props }: ComponentProps<typeof S.Label>) {
  return (
    <S.Label
      className={cn(
        "px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-muted",
        className,
      )}
      {...props}
    />
  );
}

export function SelectSeparator({ className, ...props }: ComponentProps<typeof S.Separator>) {
  return <S.Separator className={cn("-mx-1 my-1 h-px bg-line", className)} {...props} />;
}

export interface SelectOption {
  value: string;
  label: ReactNode;
  disabled?: boolean;
}

export interface CustomSelectProps {
  id?: string;
  name?: string;
  value?: string | number;
  defaultValue?: string | number;
  onValueChange?: (value: string) => void;
  onChange?: (e: { target: { value: string } }) => void;
  options?: SelectOption[];
  children?: ReactNode;
  placeholder?: string;
  disabled?: boolean;
  required?: boolean;
  className?: string;
  triggerClassName?: string;
  contentClassName?: string;
  size?: "sm" | "md";
  title?: string;
  "aria-label"?: string;
  "aria-invalid"?: boolean;
  "aria-describedby"?: string;
}

const EMPTY_VALUE = "__EMPTY__";

/**
 * Sayt dizayniga moslashtirilgan umumiy Select komponenti.
 *
 * 2 xil usulda ishlatish mumkin:
 * 1. `options` massivini berish:
 *    `<CustomSelect value={val} onValueChange={setVal} options={[{ value: '1', label: 'Bir' }]} />`
 * 2. Standart `<option>` bolalarini berish:
 *    `<CustomSelect value={val} onChange={(e) => setVal(e.target.value)}>
 *       <option value="1">Bir</option>
 *     </CustomSelect>`
 */
export function CustomSelect({
  id,
  value,
  defaultValue,
  onValueChange,
  onChange,
  options,
  children,
  placeholder,
  disabled,
  className,
  triggerClassName,
  contentClassName,
  size = "md",
  title,
  "aria-label": ariaLabel,
  "aria-invalid": ariaInvalid,
}: CustomSelectProps) {
  // Optionlarni yig'ish (props yoki children orqali)
  const items: SelectOption[] = [];

  if (options) {
    items.push(...options);
  } else if (children) {
    Children.forEach(children, (child) => {
      if (!isValidElement(child)) return;
      const p = child.props as Record<string, any>;
      items.push({
        value: String(p.value ?? ""),
        label: p.children ?? String(p.value ?? ""),
        disabled: Boolean(p.disabled),
      });
    });
  }

  // Bo'sh qiymatlarni (placeholder/all) Radix Select bilan moslash
  const toInternalValue = (v: string | number | undefined) => {
    if (v === undefined || v === null) return undefined;
    const str = String(v);
    return str === "" ? EMPTY_VALUE : str;
  };

  const fromInternalValue = (v: string) => {
    return v === EMPTY_VALUE ? "" : v;
  };

  const handleValueChange = (newVal: string) => {
    const actual = fromInternalValue(newVal);
    onValueChange?.(actual);
    onChange?.({ target: { value: actual } });
  };

  const internalValue = toInternalValue(value);
  const internalDefault = toInternalValue(defaultValue);

  return (
    <Select
      value={internalValue}
      defaultValue={internalDefault}
      onValueChange={handleValueChange}
      disabled={disabled}
    >
      <SelectTrigger
        id={id}
        size={size}
        title={title}
        aria-label={ariaLabel ?? title}
        aria-invalid={ariaInvalid}
        className={cn(className, triggerClassName)}
      >
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent className={contentClassName}>
        {items.map((opt, idx) => (
          <SelectItem
            key={`${toInternalValue(opt.value)}-${idx}`}
            value={toInternalValue(opt.value) ?? EMPTY_VALUE}
            disabled={opt.disabled}
            size={size}
          >
            {opt.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export { CustomSelect as SelectField };
