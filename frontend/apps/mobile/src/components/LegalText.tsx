/** Javob/baho matni: **qalin**, «iqtibos», [M#] — lex.uz havolasi (tekshiruvdan keyin yashil, berilmagan — qizil). */
import * as WebBrowser from "expo-web-browser";
import { Text, View } from "react-native";

import { colors, fonts, tint } from "@/lib/theme";

export interface CiteSource {
  key: string;
  doc_title: string;
  label: string;
  lex_url: string;
}

const TOKEN_RE = /(\*\*[^*]+\*\*|«[^»]+»|\[M\d+\])/g;

function Inline({ text, sources, cited }: { text: string; sources: Record<string, CiteSource>; cited?: Set<string> }) {
  return (
    <>
      {text.split(TOKEN_RE).map((part, i) => {
        if (!part) return null;
        if (part.startsWith("**") && part.endsWith("**")) return <Text key={i} style={{ fontFamily: fonts.semibold }}>{part.slice(2, -2)}</Text>;
        if (part.startsWith("«")) return <Text key={i} style={{ color: colors.quote, backgroundColor: tint(colors.primary, 0.08) }}>{part}</Text>;
        const m = /^\[(M\d+)\]$/.exec(part);
        if (m) {
          const src = sources[m[1]];
          const color = !src ? colors.red : cited?.has(m[1]) ? colors.green : colors.gold;
          return (
            <Text key={i} onPress={src ? () => void WebBrowser.openBrowserAsync(src.lex_url) : undefined}
              style={{ color, fontFamily: fonts.semibold, fontSize: 13 }}>{` ${m[1]} `}</Text>
          );
        }
        return part;
      })}
    </>
  );
}

/** Oddiy markdown: sarlavha (#), ro'yxat (-, 1.), jadval qatorlari matn sifatida, chiziq. */
export function LegalText({ text, sources = {}, cited, streaming }: {
  text: string; sources?: Record<string, CiteSource>; cited?: Set<string>; streaming?: boolean;
}) {
  const lines = text.split("\n");
  return (
    <View style={{ gap: 8 }}>
      {lines.map((raw, i) => {
        const line = raw.trimEnd();
        if (!line.trim()) return null;
        if (/^-{3,}$/.test(line.trim())) return <View key={i} style={{ height: 1, backgroundColor: colors.line, marginVertical: 4 }} />;
        if (/^\s*\|[\s:|-]+\|\s*$/.test(line)) return null; // jadval ajratgichi
        const h = /^(#{1,3}) (.*)$/.exec(line);
        const li = /^\s*([-*]|\d+\.) (.*)$/.exec(line);
        const body = h ? h[2] : li ? li[2] : line.replace(/^\s*\|/, "").replace(/\|\s*$/, "").replace(/\s*\|\s*/g, " · ");
        const last = i === lines.length - 1 && streaming;
        return (
          <Text key={i} style={{ color: colors.ink, fontSize: h ? 18 : 16, lineHeight: h ? 25 : 26, fontFamily: h ? fonts.serif : fonts.regular, marginTop: h ? 8 : 0 }}>
            {li ? <Text style={{ color: colors.muted }}>{li[1].endsWith(".") ? `${li[1]} ` : "•  "}</Text> : null}
            <Inline text={body} sources={sources} cited={cited} />
            {last ? <Text style={{ color: colors.primary }}>▍</Text> : null}
          </Text>
        );
      })}
    </View>
  );
}
