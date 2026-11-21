/**
 * designs/mezon_klassik/DESIGN.md tokenlari (veb `theme.css` bilan bir xil qiymatlar).
 * `colors` — joriy palitra (o'zgaruvchan obyekt): rejim almashganda `setPalette` uni yangilaydi, ThemeProvider esa
 * navigatorni qayta chizadi — komponentlar `colors.x` ni render paytida o'qigani uchun yangi rang oladi.
 */
export type Mode = "light" | "dark";

const light = {
  canvas: "#F7F4EC",
  surface: "#FFFFFF",
  subtle: "#F1ECE0",
  line: "#E4DCCB",
  ink: "#1D2433",
  muted: "#6B6658",
  primary: "#1F3A5F",
  primaryFg: "#FFFFFF",
  gold: "#8A6A1F",
  green: "#2F7D4F",
  red: "#B4382F",
  amber: "#A9671A",
  quote: "#34465F",
};

const dark: typeof light = {
  canvas: "#17181B",
  surface: "#1F2024",
  subtle: "#292A2F",
  line: "#34353B",
  ink: "#ECEAE4",
  muted: "#A19D93",
  primary: "#9DBBE0",
  primaryFg: "#10213A",
  gold: "#D9B565",
  green: "#6CC08F",
  red: "#EB7B70",
  amber: "#E2A65A",
  quote: "#C9D6E8",
};

export const palettes = { light, dark } as const;
export type Palette = typeof light;

export const colors: Palette = { ...light };
export let mode: Mode = "light";

export function setPalette(next: Mode) {
  mode = next;
  Object.assign(colors, palettes[next]);
}

/** Rangni shaffoflik bilan: tint("#2F7D4F", 0.12) -> "rgba(47,125,79,0.12)" */
export function tint(hex: string, alpha: number): string {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${alpha})`;
}

/** Shriftlar (expo-font, _layout.tsx da yuklanadi). Android da fontWeight emas — aniq oila nomi. */
export const fonts = {
  regular: "Inter_400Regular",
  medium: "Inter_500Medium",
  semibold: "Inter_600SemiBold",
  serif: "Lora_600SemiBold",
} as const;

export const radius = { sm: 8, md: 12, lg: 16 } as const;
