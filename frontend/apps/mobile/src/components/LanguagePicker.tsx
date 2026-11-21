import { LANGUAGES } from "@mezon/i18n";
import { Pressable, Text, View } from "react-native";

import { useLanguage } from "@/lib/i18n";
import { colors, fonts, tint } from "@/lib/theme";

/** 5 til, har biri o'z yozuvida */
export function LanguagePicker() {
  const { language, setLanguage } = useLanguage();
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
      {LANGUAGES.map((l) => (
        <Pressable key={l.code} onPress={() => setLanguage(l.code)} accessibilityRole="button" accessibilityState={{ selected: language === l.code }}
          style={{ paddingHorizontal: 14, paddingVertical: 8, borderRadius: 999, borderWidth: 1,
            borderColor: language === l.code ? colors.primary : colors.line, backgroundColor: language === l.code ? tint(colors.primary, 0.1) : colors.surface }}>
          <Text style={{ color: language === l.code ? colors.primary : colors.muted, fontSize: 14, fontFamily: language === l.code ? fonts.semibold : fonts.regular }}>{l.name}</Text>
        </Pressable>
      ))}
    </View>
  );
}
