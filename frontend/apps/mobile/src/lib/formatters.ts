/**
 * MEZON AI — Inputlarni formatlash yordamchilari (Telefon, Raqam, Pul).
 */

/**
 * Telefon raqamidan faqat mahalliy 9 ta raqamni ajratib oladi.
 * Masalan: "+998901234567" -> "901234567", "998901234567" -> "901234567",
 *          "8901234567" -> "901234567", "90 123 45 67" -> "901234567".
 */
export function extractUzDigits(input: string | null | undefined): string {
  if (!input) return "";
  let digits = String(input).replace(/\D/g, "");
  if (digits.startsWith("998")) {
    digits = digits.slice(3);
  } else if (digits.startsWith("8") && digits.length === 10) {
    digits = digits.slice(1);
  }
  return digits.slice(0, 9);
}

/**
 * 9 ta mahalliy raqamni chiroyli va qulay formatga keltiradi:
 * "90" -> "90"
 * "901" -> "90 1"
 * "90123" -> "90 123"
 * "9012345" -> "90 123 45"
 * "901234567" -> "90 123 45 67" (aniq 12 ta belgi!)
 */
export function formatUzDisplay(rawDigits: string): string {
  if (!rawDigits) return "";
  let res = rawDigits.slice(0, 2);
  if (rawDigits.length > 2) {
    res += " " + rawDigits.slice(2, 5);
  }
  if (rawDigits.length > 5) {
    res += " " + rawDigits.slice(5, 7);
  }
  if (rawDigits.length > 7) {
    res += " " + rawDigits.slice(7, 9);
  }
  return res;
}

/**
 * O'zbekiston telefon raqamini to'liq qayta ishlash funksiyasi.
 */
export function formatUzPhone(input: string): { display: string; normalized: string; rawDigits: string } {
  const rawDigits = extractUzDigits(input);
  const display = formatUzDisplay(rawDigits);
  const normalized = rawDigits.length > 0 ? `+998${rawDigits}` : "";
  return { display, normalized, rawDigits };
}

/**
 * Raqamlarni minglik ajratgich bilan formatlash: "1000000" -> "1 000 000"
 */
export function formatNumber(input: string | number | null | undefined): string {
  if (input === "" || input === null || input === undefined) return "";
  const numStr = String(input).replace(/\D/g, "");
  if (!numStr) return "";
  return numStr.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

/**
 * Formatlangan raqamdan xom sonni olish: "1 000 000" -> 1000000
 */
export function parseNumber(input: string): number {
  if (!input) return 0;
  const clean = input.replace(/\s+/g, "");
  return clean ? Number(clean) : 0;
}
