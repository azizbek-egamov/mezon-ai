import { Text, View } from "react-native";

import { colors, fonts } from "@/lib/theme";

/** Logotip (designs/mezon_klassik): to'q ko'k kvadratda oltin serif "M" + "Mezon" */
export function Brand({ size = 40 }: { size?: number }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 4 }}>
      <View style={{ width: size, height: size, borderRadius: size / 4, backgroundColor: "#1F3A5F", alignItems: "center", justifyContent: "center" }}>
        <Text style={{ color: "#E2C77E", fontFamily: fonts.serif, fontSize: size * 0.58, lineHeight: size * 0.8 }}>M</Text>
      </View>
      <Text style={{ color: colors.ink, fontFamily: fonts.serif, fontSize: size * 0.6 }}>Mezon</Text>
    </View>
  );
}
