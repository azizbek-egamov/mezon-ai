import {
  CalendarIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  XIcon,
} from "lucide-react";
import { Popover as P } from "radix-ui";
import {
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent,
} from "react";

import { LanguageContext, type LanguageContextValue } from "../lib/i18n";
import { cn } from "../lib/utils";

interface I18nCalendar {
  months: string[];
  weekdays: string[];
  today: string;
  clear: string;
  placeholder: string;
}

const CALENDAR_I18N: Record<string, I18nCalendar> = {
  "uz-Latn": {
    months: [
      "Yanvar",
      "Fevral",
      "Mart",
      "Aprel",
      "May",
      "Iyun",
      "Iyul",
      "Avgust",
      "Sentabr",
      "Oktabr",
      "Noyabr",
      "Dekabr",
    ],
    weekdays: ["Du", "Se", "Cho", "Pay", "Ju", "Sha", "Yak"],
    today: "Bugun",
    clear: "Tozalash",
    placeholder: "kk.oo.yyyy",
  },
  "uz-Cyrl": {
    months: [
      "Январь",
      "Февраль",
      "Март",
      "Апрель",
      "Май",
      "Июнь",
      "Июль",
      "Август",
      "Сентябрь",
      "Октябрь",
      "Ноябрь",
      "Декабрь",
    ],
    weekdays: ["Дш", "Сш", "Чш", "Пш", "Жм", "Шн", "Як"],
    today: "Бугун",
    clear: "Тозалаш",
    placeholder: "кк.оо.йййй",
  },
  ru: {
    months: [
      "Январь",
      "Февраль",
      "Март",
      "Апрель",
      "Май",
      "Июнь",
      "Июль",
      "Август",
      "Сентябрь",
      "Октябрь",
      "Ноябрь",
      "Декабрь",
    ],
    weekdays: ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
    today: "Сегодня",
    clear: "Очистить",
    placeholder: "дд.мм.гггг",
  },
  kaa: {
    months: [
      "Yanvar",
      "Fevral",
      "Mart",
      "Aprel",
      "May",
      "Iyun",
      "Iyul",
      "Avgust",
      "Sentyabr",
      "Oktyabr",
      "Noyabr",
      "Dekabr",
    ],
    weekdays: ["Dú", "Se", "Shó", "Psh", "Jm", "Shn", "Ek"],
    today: "Búgin",
    clear: "Tazalaw",
    placeholder: "kk.oo.yyyy",
  },
  en: {
    months: [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
    ],
    weekdays: ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"],
    today: "Today",
    clear: "Clear",
    placeholder: "dd.mm.yyyy",
  },
};

function parseIso(iso?: string): Date | null {
  if (!iso || typeof iso !== "string") return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso.trim());
  if (!match) return null;
  const y = Number(match[1]);
  const m = Number(match[2]) - 1;
  const d = Number(match[3]);
  const date = new Date(y, m, d);
  if (
    date.getFullYear() !== y ||
    date.getMonth() !== m ||
    date.getDate() !== d
  ) {
    return null;
  }
  return date;
}

function toIso(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function formatDisplay(iso?: string): string {
  const date = parseIso(iso);
  if (!date) return "";
  const d = String(date.getDate()).padStart(2, "0");
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const y = date.getFullYear();
  return `${d}.${m}.${y}`;
}

export interface DatePickerProps {
  value?: string; // "YYYY-MM-DD" yoki ""
  onChange?: (value: string) => void;
  placeholder?: string;
  size?: "sm" | "md";
  disabled?: boolean;
  min?: string; // "YYYY-MM-DD"
  max?: string; // "YYYY-MM-DD"
  className?: string;
  id?: string;
  name?: string;
  required?: boolean;
  title?: string;
  "aria-label"?: string;
  "aria-invalid"?: boolean;
}

export function DatePicker({
  value = "",
  onChange,
  placeholder,
  size = "md",
  disabled = false,
  min,
  max,
  className,
  id,
  name,
  required,
  title,
  "aria-label": ariaLabel,
  "aria-invalid": ariaInvalid,
}: DatePickerProps) {
  const langCtx = useContext(LanguageContext) as LanguageContextValue | null;
  const lang = (langCtx?.language ?? "uz-Latn") as string;
  const i18n = CALENDAR_I18N[lang] ?? CALENDAR_I18N["uz-Latn"];

  const [open, setOpen] = useState(false);
  const [monthOpen, setMonthOpen] = useState(false);
  const [yearOpen, setYearOpen] = useState(false);

  // Tanlangan sana yoki hozirgi sana bo'yicha ko'rinish
  const selectedDate = useMemo(() => parseIso(value), [value]);
  const today = useMemo(() => new Date(), []);
  const todayIso = useMemo(() => toIso(today), [today]);

  const [viewYear, setViewYear] = useState(() =>
    selectedDate ? selectedDate.getFullYear() : today.getFullYear(),
  );
  const [viewMonth, setViewMonth] = useState(() =>
    selectedDate ? selectedDate.getMonth() : today.getMonth(),
  );

  const selectedYearRef = useRef<HTMLButtonElement | null>(null);

  // Popover ochilganda yoki value o'zgarganda ko'rinishni yangilash
  useEffect(() => {
    if (selectedDate) {
      setViewYear(selectedDate.getFullYear());
      setViewMonth(selectedDate.getMonth());
    }
  }, [selectedDate, open]);

  // Popover yopilganda ichki menyularni ham yopish
  const handleOpenChange = useCallback((nextOpen: boolean) => {
    setOpen(nextOpen);
    if (!nextOpen) {
      setMonthOpen(false);
      setYearOpen(false);
    }
  }, []);

  const prevMonth = useCallback(() => {
    setMonthOpen(false);
    setYearOpen(false);
    setViewMonth((m) => {
      if (m === 0) {
        setViewYear((y) => y - 1);
        return 11;
      }
      return m - 1;
    });
  }, []);

  const nextMonth = useCallback(() => {
    setMonthOpen(false);
    setYearOpen(false);
    setViewMonth((m) => {
      if (m === 11) {
        setViewYear((y) => y + 1);
        return 0;
      }
      return m + 1;
    });
  }, []);

  // Yillar ro'yxati (1940 dan 2050 gacha, o'sish tartibida)
  const years = useMemo(() => {
    const list: number[] = [];
    const currentYear = today.getFullYear();
    const startYear = Math.min(1940, currentYear - 80);
    const endYear = Math.max(2050, currentYear + 25);
    for (let y = startYear; y <= endYear; y++) {
      list.push(y);
    }
    return list;
  }, [today]);

  // Yil menyusi ochilganda joriy yilga scroll qilish
  useEffect(() => {
    if (yearOpen && selectedYearRef.current) {
      selectedYearRef.current.scrollIntoView({ block: "center" });
    }
  }, [yearOpen]);

  // Kalendar katakchalarini hisoblash
  const cells = useMemo(() => {
    const minIso = min ? min.trim() : undefined;
    const maxIso = max ? max.trim() : undefined;

    const firstDay = new Date(viewYear, viewMonth, 1);
    const startDayOfWeek = (firstDay.getDay() + 6) % 7; // Dushanba = 0
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const daysInPrevMonth = new Date(viewYear, viewMonth, 0).getDate();

    interface CellData {
      iso: string;
      day: number;
      isCurrentMonth: boolean;
      isToday: boolean;
      isSelected: boolean;
      isDisabled: boolean;
    }

    const result: CellData[] = [];

    // O'tgan oydan qolgan kunlar
    for (let i = startDayOfWeek - 1; i >= 0; i--) {
      const d = daysInPrevMonth - i;
      const prevDate = new Date(viewYear, viewMonth - 1, d);
      const iso = toIso(prevDate);
      result.push({
        iso,
        day: d,
        isCurrentMonth: false,
        isToday: iso === todayIso,
        isSelected: iso === value,
        isDisabled: Boolean(
          (minIso && iso < minIso) || (maxIso && iso > maxIso),
        ),
      });
    }

    // Joriy oy kunlari
    for (let d = 1; d <= daysInMonth; d++) {
      const curDate = new Date(viewYear, viewMonth, d);
      const iso = toIso(curDate);
      result.push({
        iso,
        day: d,
        isCurrentMonth: true,
        isToday: iso === todayIso,
        isSelected: iso === value,
        isDisabled: Boolean(
          (minIso && iso < minIso) || (maxIso && iso > maxIso),
        ),
      });
    }

    // Keyingi oydan kunlar (katakchalar 35 yoki 42 ta to'liq bo'lishi uchun)
    const totalNeeded = result.length > 35 ? 42 : 35;
    const remaining = totalNeeded - result.length;
    for (let d = 1; d <= remaining; d++) {
      const nextDate = new Date(viewYear, viewMonth + 1, d);
      const iso = toIso(nextDate);
      result.push({
        iso,
        day: d,
        isCurrentMonth: false,
        isToday: iso === todayIso,
        isSelected: iso === value,
        isDisabled: Boolean(
          (minIso && iso < minIso) || (maxIso && iso > maxIso),
        ),
      });
    }

    return result;
  }, [viewYear, viewMonth, todayIso, value, min, max]);

  const selectDate = useCallback(
    (iso: string) => {
      onChange?.(iso);
      setOpen(false);
      setMonthOpen(false);
      setYearOpen(false);
    },
    [onChange],
  );

  const clearDate = useCallback(
    (e?: MouseEvent | KeyboardEvent) => {
      e?.stopPropagation();
      e?.preventDefault();
      onChange?.("");
    },
    [onChange],
  );

  const selectToday = useCallback(() => {
    onChange?.(todayIso);
    setOpen(false);
    setMonthOpen(false);
    setYearOpen(false);
  }, [onChange, todayIso]);

  const formattedDisplay = formatDisplay(value);
  const placeholderText = placeholder || i18n.placeholder;

  return (
    <P.Root open={open} onOpenChange={handleOpenChange}>
      <P.Trigger asChild>
        {size === "sm" ? (
          <button
            type="button"
            id={id}
            disabled={disabled}
            title={title}
            aria-label={ariaLabel || title || placeholderText}
            aria-invalid={ariaInvalid}
            aria-required={required}
            className={cn(
              "group inline-flex h-8 shrink-0 items-center gap-1.5 rounded-lg bg-subtle px-2.5 text-[13px] text-ink transition-colors",
              "border border-transparent hover:border-line hover:bg-subtle/80 outline-none",
              "focus-visible:border-primary focus-visible:shadow-glow disabled:cursor-not-allowed disabled:opacity-50 select-none",
              !value && "text-muted",
              className,
            )}
          >
            {name && <input type="hidden" name={name} value={value} required={required} />}
            <CalendarIcon className="size-3.5 shrink-0 text-muted group-hover:text-ink transition-colors" />
            <span
              className={cn(
                "tabular-nums font-medium",
                !value && "font-normal text-muted",
              )}
            >
              {formattedDisplay || placeholderText}
            </span>
            {value && !disabled && (
              <span
                role="button"
                tabIndex={0}
                onClick={clearDate}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") clearDate(e);
                }}
                className="ml-0.5 rounded-full p-0.5 text-muted hover:bg-surface hover:text-ink transition-colors"
                title={i18n.clear}
                aria-label={i18n.clear}
              >
                <XIcon className="size-3" />
              </span>
            )}
          </button>
        ) : (
          <button
            type="button"
            id={id}
            disabled={disabled}
            title={title}
            aria-label={ariaLabel || title || placeholderText}
            aria-invalid={ariaInvalid}
            aria-required={required}
            className={cn(
              "group flex h-11 w-full items-center justify-between rounded-lg border border-line bg-surface px-3.5 text-[15px] text-ink transition-[border,box-shadow]",
              "hover:border-line/80 outline-none focus-visible:border-primary focus-visible:shadow-glow disabled:cursor-not-allowed disabled:opacity-50 select-none",
              ariaInvalid && "border-red",
              className,
            )}
          >
            {name && <input type="hidden" name={name} value={value} required={required} />}
            <div className="flex items-center gap-2.5 overflow-hidden">
              <CalendarIcon className="size-4 shrink-0 text-muted group-hover:text-ink transition-colors" />
              <span
                className={cn(
                  "truncate tabular-nums",
                  !value && "text-muted/70 font-normal",
                )}
              >
                {formattedDisplay || placeholderText}
              </span>
            </div>
            {value && !disabled ? (
              <span
                role="button"
                tabIndex={0}
                onClick={clearDate}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") clearDate(e);
                }}
                className="rounded-md p-1 text-muted hover:bg-subtle hover:text-ink transition-colors"
                title={i18n.clear}
                aria-label={i18n.clear}
              >
                <XIcon className="size-3.5" />
              </span>
            ) : (
              <span className="size-3.5" />
            )}
          </button>
        )}
      </P.Trigger>

      <P.Portal>
        <P.Content
          align="start"
          sideOffset={6}
          className={cn(
            "relative z-50 w-[284px] rounded-2xl border border-line bg-surface p-3 text-ink shadow-overlay outline-none select-none",
            "data-[state=open]:animate-in-scale",
          )}
        >
          {/* Sarlavha: Oy, Yil va Navigatsiya */}
          <div className="flex items-center justify-between gap-1 pb-2">
            <button
              type="button"
              onClick={prevMonth}
              className="flex size-7 items-center justify-center rounded-lg text-muted hover:bg-subtle hover:text-ink transition-colors"
              aria-label="Oldingi oy"
            >
              <ChevronLeftIcon className="size-4" />
            </button>

            <div className="flex items-center gap-1.5">
              {/* Maxsus dizayndagi Oy selektori */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => {
                    setMonthOpen((o) => !o);
                    setYearOpen(false);
                  }}
                  className={cn(
                    "inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[13px] font-semibold text-ink transition-colors",
                    "hover:bg-subtle hover:text-primary outline-none",
                    monthOpen && "bg-subtle text-primary",
                  )}
                  aria-haspopup="listbox"
                  aria-expanded={monthOpen}
                  aria-label="Oy tanlash"
                >
                  <span>{i18n.months[viewMonth]}</span>
                  <ChevronDownIcon
                    className={cn(
                      "size-3.5 text-muted transition-transform duration-200",
                      monthOpen && "rotate-180 text-primary",
                    )}
                  />
                </button>

                {monthOpen && (
                  <>
                    <div
                      className="fixed inset-0 z-20"
                      onClick={(e) => {
                        e.stopPropagation();
                        setMonthOpen(false);
                      }}
                    />
                    <div
                      role="listbox"
                      className="absolute left-0 top-full z-30 mt-1 max-h-56 w-36 overflow-y-auto rounded-xl border border-line bg-surface p-1 shadow-overlay outline-none"
                    >
                      {i18n.months.map((m, idx) => {
                        const isSelected = viewMonth === idx;
                        return (
                          <button
                            key={idx}
                            type="button"
                            role="option"
                            aria-selected={isSelected}
                            onClick={(e) => {
                              e.stopPropagation();
                              setViewMonth(idx);
                              setMonthOpen(false);
                            }}
                            className={cn(
                              "flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-[13px] transition-colors outline-none",
                              isSelected
                                ? "bg-primary/10 font-semibold text-primary"
                                : "text-ink hover:bg-subtle",
                            )}
                          >
                            <span>{m}</span>
                            {isSelected && (
                              <CheckIcon className="size-3.5 text-primary shrink-0" />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>

              {/* Maxsus dizayndagi Yil selektori */}
              <div className="relative">
                <button
                  type="button"
                  onClick={() => {
                    setYearOpen((o) => !o);
                    setMonthOpen(false);
                  }}
                  className={cn(
                    "inline-flex items-center gap-1 rounded-lg px-2 py-1 text-[13px] font-semibold text-ink transition-colors tabular-nums",
                    "hover:bg-subtle hover:text-primary outline-none",
                    yearOpen && "bg-subtle text-primary",
                  )}
                  aria-haspopup="listbox"
                  aria-expanded={yearOpen}
                  aria-label="Yil tanlash"
                >
                  <span>{viewYear}</span>
                  <ChevronDownIcon
                    className={cn(
                      "size-3.5 text-muted transition-transform duration-200",
                      yearOpen && "rotate-180 text-primary",
                    )}
                  />
                </button>

                {yearOpen && (
                  <>
                    <div
                      className="fixed inset-0 z-20"
                      onClick={(e) => {
                        e.stopPropagation();
                        setYearOpen(false);
                      }}
                    />
                    <div
                      role="listbox"
                      className="absolute right-0 top-full z-30 mt-1 max-h-56 w-28 overflow-y-auto rounded-xl border border-line bg-surface p-1 shadow-overlay outline-none"
                    >
                      {years.map((y) => {
                        const isSelected = viewYear === y;
                        return (
                          <button
                            key={y}
                            type="button"
                            role="option"
                            aria-selected={isSelected}
                            ref={isSelected ? selectedYearRef : undefined}
                            onClick={(e) => {
                              e.stopPropagation();
                              setViewYear(y);
                              setYearOpen(false);
                            }}
                            className={cn(
                              "flex w-full items-center justify-between rounded-lg px-2.5 py-1.5 text-left text-[13px] tabular-nums transition-colors outline-none",
                              isSelected
                                ? "bg-primary/10 font-semibold text-primary"
                                : "text-ink hover:bg-subtle",
                            )}
                          >
                            <span>{y}</span>
                            {isSelected && (
                              <CheckIcon className="size-3.5 text-primary shrink-0" />
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>
            </div>

            <button
              type="button"
              onClick={nextMonth}
              className="flex size-7 items-center justify-center rounded-lg text-muted hover:bg-subtle hover:text-ink transition-colors"
              aria-label="Keyingi oy"
            >
              <ChevronRightIcon className="size-4" />
            </button>
          </div>

          {/* Hafta kunlari */}
          <div className="grid grid-cols-7 gap-1 pt-1 text-center">
            {i18n.weekdays.map((w, idx) => (
              <span
                key={idx}
                className="text-[11px] font-semibold text-muted/70 uppercase tracking-wider"
              >
                {w}
              </span>
            ))}
          </div>

          {/* Kunlar to'ri (Grid) */}
          <div className="mt-1.5 grid grid-cols-7 gap-1">
            {cells.map((cell, idx) => (
              <button
                key={`${cell.iso}-${idx}`}
                type="button"
                disabled={cell.isDisabled}
                onClick={() => selectDate(cell.iso)}
                className={cn(
                  "flex size-8 items-center justify-center rounded-lg text-[13px] font-medium transition-colors tabular-nums",
                  cell.isSelected &&
                    "bg-primary font-semibold text-primary-fg shadow-sm hover:bg-primary/90",
                  !cell.isSelected &&
                    cell.isToday &&
                    "border border-primary/50 font-semibold text-primary hover:bg-subtle",
                  !cell.isSelected &&
                    !cell.isToday &&
                    cell.isCurrentMonth &&
                    "text-ink hover:bg-subtle",
                  !cell.isSelected &&
                    !cell.isToday &&
                    !cell.isCurrentMonth &&
                    "text-muted/40 hover:bg-subtle/50",
                  cell.isDisabled &&
                    "cursor-not-allowed opacity-25 pointer-events-none",
                )}
              >
                {cell.day}
              </button>
            ))}
          </div>

          {/* Pastki amallar paneli (Bugun va Tozalash) */}
          <div className="mt-2.5 flex items-center justify-between border-t border-line/60 pt-2">
            <button
              type="button"
              onClick={() => {
                onChange?.("");
                setOpen(false);
                setMonthOpen(false);
                setYearOpen(false);
              }}
              className="rounded px-2 py-1 text-xs text-muted hover:bg-subtle hover:text-ink transition-colors"
            >
              {i18n.clear}
            </button>

            <button
              type="button"
              onClick={selectToday}
              className="rounded px-2 py-1 text-xs font-semibold text-primary hover:bg-subtle hover:text-primary/80 transition-colors"
            >
              {i18n.today}
            </button>
          </div>
        </P.Content>
      </P.Portal>
    </P.Root>
  );
}
