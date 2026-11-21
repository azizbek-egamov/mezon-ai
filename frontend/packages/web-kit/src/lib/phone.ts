/** Oʻzbekiston telefon raqamidan mahalliy 9 ta raqamni ajratadi. */
export function extractUzPhoneDigits(input: string | null | undefined): string {
  if (!input) return "";
  let digits = String(input).replace(/\D/g, "");
  if (digits.startsWith("998")) digits = digits.slice(3);
  else if (digits.startsWith("8") && digits.length === 10) digits = digits.slice(1);
  return digits.slice(0, 9);
}

/** 901234567 -> 90 123 45 67. */
export function formatUzPhoneDisplay(digits: string): string {
  const value = digits.slice(0, 9);
  if (!value) return "";
  const parts = [value.slice(0, 2)];
  if (value.length > 2) parts.push(value.slice(2, 5));
  if (value.length > 5) parts.push(value.slice(5, 7));
  if (value.length > 7) parts.push(value.slice(7, 9));
  return parts.join(" ");
}

export function formatUzPhone(input: string): { display: string; normalized: string; digits: string } {
  const digits = extractUzPhoneDigits(input);
  return {
    digits,
    display: formatUzPhoneDisplay(digits),
    normalized: digits ? `+998${digits}` : "",
  };
}
