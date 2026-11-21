/** Mobil UI: designs/mezon_klassik/DESIGN.md — iliq oq fon, serif sarlavhalar, to'q ko'k asosiy amal, boy animatsiyalar. */
import { MaterialCommunityIcons } from "@expo/vector-icons";
import type { ReactNode } from "react";
import { useState } from "react";
import {
  ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
  type PressableProps, type StyleProp, type TextInputProps, type TextProps, type ViewStyle,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Animated, {
  FadeIn, FadeInDown, FadeInUp, useAnimatedStyle, useSharedValue, withSpring, withTiming
} from "react-native-reanimated";

import { colors, fonts, radius, tint } from "@/lib/theme";
import { extractUzDigits, formatNumber, formatUzDisplay, formatUzPhone, parseNumber } from "@/lib/formatters";

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

/** Veb-rejimda brauzerning standart fokus ramkasi (oq to'rtburchak) o'chiriladi — fokus holatini konteyner chegarasi
 * (`colors.primary`) ko'rsatadi. Telefonda (native) hech narsa o'zgarmaydi. */
export const noOutline = (Platform.OS === "web" ? { outlineStyle: "none", outlineWidth: 0 } : {}) as object;

export function Screen({
  children,
  scroll = true,
  refreshControl,
  style,
  header = false,
  animated = true,
  keyboardOffset = 0,
  scrollViewRef,
}: {
  children: ReactNode;
  scroll?: boolean;
  refreshControl?: React.ReactElement<any>;
  style?: StyleProp<ViewStyle>;
  /** ekran ustida navigatsiya sarlavhasi bor (u tepadagi joyni o'zi oladi) */
  header?: boolean;
  animated?: boolean;
  keyboardOffset?: number;
  scrollViewRef?: React.Ref<any>;
}) {
  const content = scroll ? (
    <ScrollView
      ref={scrollViewRef}
      contentContainerStyle={[s.content, { flexGrow: 1, paddingBottom: 140 }, style]}
      refreshControl={refreshControl}
      keyboardShouldPersistTaps="always"
      keyboardDismissMode="on-drag"
      showsVerticalScrollIndicator={false}
    >
      {children}
    </ScrollView>
  ) : (
    <View style={[s.content, { flex: 1 }, style]}>{children}</View>
  );

  const inner = (
    <SafeAreaView style={s.screen} edges={header ? ["left", "right"] : ["top", "left", "right"]}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={Platform.OS === "ios" ? (header ? 88 : 20) : keyboardOffset}
      >
        {content}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );

  return inner;
}

type Variant = "title" | "h2" | "body" | "muted" | "small" | "mono" | "label";
export function Txt({ variant = "body", style, ...props }: TextProps & { variant?: Variant }) {
  return <Text style={[s[variant], style]} {...props} />;
}

type Accent = "primary" | "green" | "red" | "amber" | "gold";
export function Card({
  children, accent, style, delay = 0, noAnimation = false
}: {
  children: ReactNode; accent?: Accent; style?: StyleProp<ViewStyle>; delay?: number; noAnimation?: boolean;
}) {
  const cardStyle = [s.card, accent && { borderLeftWidth: 3, borderLeftColor: colors[accent] }, style];
  return <View style={cardStyle}>{children}</View>;
}

type ButtonVariant = "primary" | "outline" | "gold" | "danger" | "ghost";
export function Button({ title, variant = "primary", loading, icon, style, disabled, ...props }: PressableProps & {
  title: string; variant?: ButtonVariant; loading?: boolean; icon?: ReactNode; style?: StyleProp<ViewStyle>;
}) {
  const v = {
    primary: { bg: colors.primary, fg: colors.primaryFg, border: colors.primary },
    outline: { bg: colors.surface, fg: colors.ink, border: colors.line },
    gold: { bg: colors.surface, fg: colors.ink, border: colors.line },
    danger: { bg: colors.surface, fg: colors.red, border: tint(colors.red, 0.4) },
    ghost: { bg: "transparent", fg: colors.muted, border: "transparent" },
  }[variant];

  const scale = useSharedValue(1);
  const animStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }));

  const handlePressIn = () => {
    if (!disabled && !loading) {
      scale.value = withTiming(0.96, { duration: 100 });
    }
  };

  const handlePressOut = () => {
    if (!disabled && !loading) {
      scale.value = withSpring(1, { damping: 12, stiffness: 220 });
    }
  };

  return (
    <AnimatedPressable
      accessibilityRole="button"
      disabled={disabled || loading}
      onPressIn={handlePressIn}
      onPressOut={handlePressOut}
      style={[
        s.button,
        { backgroundColor: v.bg, borderColor: v.border, opacity: disabled ? 0.5 : 1 },
        animStyle,
        style,
      ]}
      {...props}
    >
      {loading ? <ActivityIndicator color={v.fg} size="small" /> : icon}
      <Text style={[s.buttonText, { color: v.fg }]}>{title}</Text>
    </AnimatedPressable>
  );
}

export function Field({ label, error, style, onFocus, onBlur, rightAccessory, ...props }: TextInputProps & {
  label?: string;
  error?: string[];
  rightAccessory?: ReactNode;
}) {
  const [focused, setFocused] = useState(false);

  return (
    <View style={{ gap: 8 }}>
      {label ? <Txt variant="label">{label}</Txt> : null}
      <View style={{ position: "relative" }}>
        <TextInput
          placeholderTextColor={colors.muted}
          onFocus={(e) => {
            setFocused(true);
            onFocus?.(e);
          }}
          onBlur={(e) => {
            setFocused(false);
            onBlur?.(e);
          }}
          style={[
            s.input,
            rightAccessory ? { paddingRight: 52 } : null,
            focused ? { borderColor: colors.primary, borderWidth: 1.5 } : null,
            error?.length ? { borderColor: colors.red } : null,
            style,
          ]}
          {...props}
        />
        {rightAccessory ? (
          <View style={{ position: "absolute", right: 4, top: 0, bottom: 0, justifyContent: "center" }}>
            {rightAccessory}
          </View>
        ) : null}
      </View>
      {error?.length ? (
        <Animated.View entering={FadeInUp.duration(200)}>
          <Txt variant="small" style={{ color: colors.red }}>{error.join(" ")}</Txt>
        </Animated.View>
      ) : null}
    </View>
  );
}

export function PasswordField({ revealLabel, ...props }: Omit<React.ComponentProps<typeof Field>, "secureTextEntry" | "rightAccessory"> & {
  revealLabel: string;
}) {
  const [revealed, setRevealed] = useState(false);
  return (
    <Field
      {...props}
      secureTextEntry={!revealed}
      rightAccessory={(
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={revealLabel}
          hitSlop={8}
          onPressIn={() => setRevealed(true)}
          onPressOut={() => setRevealed(false)}
          style={({ pressed }) => ({
            width: 44,
            height: 44,
            alignItems: "center",
            justifyContent: "center",
            opacity: pressed ? 0.65 : 1,
          })}
        >
          <MaterialCommunityIcons name={revealed ? "eye-outline" : "eye-off-outline"} size={22} color={colors.muted} />
        </Pressable>
      )}
    />
  );
}

/**
 * Formatlangan O'zbekiston telefon raqami inputi.
 * Chap tomonda alohida +998 prefiksi, o'ng tomonda 9 ta raqam uchun toza format (XX XXX XX XX).
 * Simkarta kodi (90...) to'liq va erkin o'chiriladi.
 * Limitga yetganda miltillash bo'lmaydi (maxLength=12).
 */
export function PhoneField({
  label, value, onChangePhone, error, style
}: {
  label?: string;
  value: string;
  onChangePhone: (normalized: string, display: string) => void;
  error?: string[];
  style?: StyleProp<ViewStyle>;
}) {
  const [focused, setFocused] = useState(false);
  const currentDigits = extractUzDigits(value || "");
  const currentDisplay = formatUzDisplay(currentDigits);

  const handleChange = (text: string) => {
    let prevDigits = extractUzDigits(currentDisplay);
    let newDigits = extractUzDigits(text);

    // Agar foydalanuvchi orqaga o'chirsa va bo'shliq belgisi sababli raqam o'chmagan bo'lsa
    if (text.length < currentDisplay.length && newDigits === prevDigits && newDigits.length > 0) {
      newDigits = newDigits.slice(0, -1);
    }

    const nextDisplay = formatUzDisplay(newDigits);
    const nextNormalized = newDigits.length > 0 ? `+998${newDigits}` : "";
    onChangePhone(nextNormalized, nextDisplay);
  };

  return (
    <View style={{ gap: 8 }}>
      {label ? <Txt variant="label">{label}</Txt> : null}
      <View style={[
        s.phoneContainer,
        focused ? { borderColor: colors.primary, borderWidth: 1.5 } : null,
        error?.length ? { borderColor: colors.red } : null,
        style
      ]}>
        <View style={s.phonePrefix}>
          <Text style={s.phonePrefixText}>+998</Text>
        </View>
        <TextInput
          value={currentDisplay}
          onChangeText={handleChange}
          placeholder="90 123 45 67"
          placeholderTextColor={colors.muted}
          keyboardType="phone-pad"
          autoComplete="tel"
          textContentType="telephoneNumber"
          maxLength={12} // 90 123 45 67 aniq 12 ta belgi — ortiqcha belgi yozilmaydi, miltillamaydi!
          numberOfLines={1}
          multiline={false}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={s.phoneInput}
        />
      </View>
      {error?.length ? (
        <Animated.View entering={FadeInUp.duration(200)}>
          <Txt variant="small" style={{ color: colors.red }}>{error.join(" ")}</Txt>
        </Animated.View>
      ) : null}
    </View>
  );
}

/**
 * Minglik ajratgich bilan formatlangan raqam inputi (summa, narx, hajm).
 */
export function NumberField({
  label, value, onChangeNumber, placeholder, error, suffix, style
}: {
  label?: string;
  value: number | string;
  onChangeNumber: (val: number, formatted: string) => void;
  placeholder?: string;
  error?: string[];
  suffix?: string;
  style?: StyleProp<ViewStyle>;
}) {
  const [focused, setFocused] = useState(false);
  const displayVal = formatNumber(value);

  const handleChange = (text: string) => {
    const num = parseNumber(text);
    const fmt = formatNumber(num);
    onChangeNumber(num, fmt);
  };

  return (
    <View style={{ gap: 8 }}>
      {label ? <Txt variant="label">{label}</Txt> : null}
      <View style={[
        s.inputContainer,
        { flexDirection: "row", alignItems: "center" },
        focused ? { borderColor: colors.primary, borderWidth: 1.5 } : null,
        error?.length ? { borderColor: colors.red } : null,
        style
      ]}>
        <TextInput
          value={displayVal}
          onChangeText={handleChange}
          placeholder={placeholder || "0"}
          placeholderTextColor={colors.muted}
          keyboardType="numeric"
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={[s.inputBare, { flex: 1 }]}
        />
        {suffix ? <Txt variant="muted" style={{ paddingRight: 14 }}>{suffix}</Txt> : null}
      </View>
      {error?.length ? (
        <Animated.View entering={FadeInUp.duration(200)}>
          <Txt variant="small" style={{ color: colors.red }}>{error.join(" ")}</Txt>
        </Animated.View>
      ) : null}
    </View>
  );
}

export type Tone = "neutral" | "ok" | "bad" | "warn" | "info" | "gold";
function toneColors(tone: Tone) {
  switch (tone) {
    case "ok": return { bg: tint(colors.green, 0.12), fg: colors.green };
    case "bad": return { bg: tint(colors.red, 0.1), fg: colors.red };
    case "warn": return { bg: tint(colors.amber, 0.12), fg: colors.amber };
    case "info": return { bg: tint(colors.primary, 0.1), fg: colors.primary };
    case "gold": return { bg: tint(colors.gold, 0.12), fg: colors.gold };
    default: return { bg: colors.subtle, fg: colors.muted };
  }
}
export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: Tone; mono?: boolean }) {
  const t = toneColors(tone);
  return (
    <View style={[s.badge, { backgroundColor: t.bg }]}>
      <Text style={[s.badgeText, { color: t.fg }]}>{children}</Text>
    </View>
  );
}

export function Progress({ value, tone = "blue" }: { value: number; tone?: "blue" | "red" }) {
  return (
    <View style={s.track}>
      <View style={[s.bar, { width: `${Math.min(100, Math.max(0, value))}%`, backgroundColor: tone === "red" ? colors.red : colors.primary }]} />
    </View>
  );
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <Animated.View entering={FadeInDown.duration(250)} style={s.error}>
      <Text style={{ color: colors.red, fontSize: 14, lineHeight: 20, fontFamily: fonts.regular }}>{children}</Text>
    </Animated.View>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <View style={{ paddingVertical: 40, alignItems: "center" }}>{typeof children === "string" ? <Txt variant="muted">{children}</Txt> : children}</View>;
}

export function Segmented<T extends string>({ value, options, onChange }: { value: T; options: { value: T; label: string }[]; onChange(v: T): void }) {
  return (
    <View style={s.segmented}>
      {options.map((o) => (
        <Pressable key={o.value} onPress={() => onChange(o.value)} accessibilityRole="radio" accessibilityState={{ selected: value === o.value }}
          style={[s.segment, value === o.value && { backgroundColor: colors.surface, elevation: 1 }]}>
          <Text style={{ color: value === o.value ? colors.ink : colors.muted, fontSize: 14, fontFamily: value === o.value ? fonts.semibold : fonts.medium }} numberOfLines={1}>{o.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

function makeStyles() {
  return StyleSheet.create({
    screen: { flex: 1, backgroundColor: colors.canvas },
    content: { paddingHorizontal: 20, paddingTop: 20, gap: 16, paddingBottom: 40 },
    title: { color: colors.ink, fontSize: 28, lineHeight: 36, fontFamily: fonts.serif },
    h2: { color: colors.ink, fontSize: 19, lineHeight: 26, fontFamily: fonts.serif },
    body: { color: colors.ink, fontSize: 16, lineHeight: 25, fontFamily: fonts.regular },
    muted: { color: colors.muted, fontSize: 15, lineHeight: 22, fontFamily: fonts.regular },
    small: { color: colors.muted, fontSize: 13, lineHeight: 19, fontFamily: fonts.regular },
    mono: { color: colors.muted, fontSize: 13, fontFamily: fonts.regular, fontVariant: ["tabular-nums"] },
    label: { color: colors.ink, fontSize: 14, fontFamily: fonts.medium },
    card: { backgroundColor: colors.surface, borderColor: colors.line, borderWidth: 1, borderRadius: radius.md, padding: 18, gap: 10 },
    button: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, minHeight: 52, paddingHorizontal: 18,
      borderRadius: radius.sm + 2, borderWidth: 1 },
    buttonText: { fontSize: 16, fontFamily: fonts.semibold },
    input: {
      backgroundColor: colors.surface,
      borderColor: colors.line,
      borderWidth: 1,
      borderRadius: radius.sm + 2,
      color: colors.ink,
      paddingHorizontal: 14,
      paddingVertical: 0,
      fontSize: 16,
      fontFamily: fonts.regular,
      height: 52,
      minHeight: 52,
      ...noOutline,
    },
    inputContainer: { backgroundColor: colors.surface, borderColor: colors.line, borderWidth: 1, borderRadius: radius.sm + 2, minHeight: 52, height: 52 },
    inputBare: { color: colors.ink, paddingHorizontal: 14, paddingVertical: 0, fontSize: 16, fontFamily: fonts.regular, height: 52, ...noOutline },
    phoneContainer: {
      flexDirection: "row",
      alignItems: "center",
      backgroundColor: colors.surface,
      borderColor: colors.line,
      borderWidth: 1,
      borderRadius: radius.sm + 2,
      overflow: "hidden",
      height: 52,
      minHeight: 52,
      maxHeight: 52,
    },
    phonePrefix: {
      backgroundColor: colors.subtle,
      paddingHorizontal: 14,
      height: 52,
      justifyContent: "center",
      alignItems: "center",
      borderRightWidth: 1,
      borderRightColor: colors.line,
    },
    phonePrefixText: { color: colors.ink, fontSize: 16, fontFamily: fonts.medium },
    phoneInput: {
      flex: 1,
      color: colors.ink,
      paddingHorizontal: 14,
      paddingVertical: 0,
      fontSize: 16,
      fontFamily: fonts.regular,
      height: 52,
      letterSpacing: 0.5,
      ...noOutline,
    },
    badge: { alignSelf: "flex-start", borderRadius: 999, paddingHorizontal: 10, paddingVertical: 3 },
    badgeText: { fontSize: 13, fontFamily: fonts.medium },
    track: { height: 8, borderRadius: 4, backgroundColor: colors.subtle, overflow: "hidden" },
    bar: { height: "100%", borderRadius: 4 },
    error: { borderWidth: 1, borderColor: tint(colors.red, 0.3), backgroundColor: tint(colors.red, 0.08), borderRadius: radius.sm + 2, padding: 12 },
    segmented: { flexDirection: "row", backgroundColor: colors.subtle, borderRadius: radius.md, padding: 4 },
    segment: { flex: 1, alignItems: "center", paddingVertical: 9, borderRadius: radius.sm },
  });
}

/** Joriy palitra bo'yicha uslublar; ThemeProvider rejim almashganda `rebuildStyles()` chaqiradi. */
export let s = makeStyles();
export function rebuildStyles() {
  s = makeStyles();
}
