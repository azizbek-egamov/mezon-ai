import { Inter_400Regular, Inter_500Medium, Inter_600SemiBold } from "@expo-google-fonts/inter";
import { Lora_600SemiBold } from "@expo-google-fonts/lora";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AuthProvider } from "@/lib/auth";
import { LanguageProvider } from "@/lib/i18n";
import { colors } from "@/lib/theme";
import { ThemeProvider } from "@/lib/themeContext";

void SplashScreen.preventAutoHideAsync();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (count, error) => count < 1 && !(error instanceof Error && "status" in error && Number(error.status) < 500),
    },
  },
});

export default function RootLayout() {
  // Shriftlar ilova ichida (APK da) — tarmoq kerak emas; yuklanguncha splash ekran turadi
  const [fontsLoaded, fontError] = useFonts({ Inter_400Regular, Inter_500Medium, Inter_600SemiBold, Lora_600SemiBold });
  const ready = fontsLoaded || !!fontError;
  useEffect(() => {
    if (ready) void SplashScreen.hideAsync();
  }, [ready]);
  if (!ready) return null;

  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <LanguageProvider>
            <ThemeProvider>
              {(mode) => (
                <>
                  <StatusBar style={mode === "dark" ? "light" : "dark"} />
                  {/* key: rejim almashganda ekranlar yangi ranglar bilan qayta chiziladi */}
                  <Stack key={mode} screenOptions={{
                    headerShown: false,
                    contentStyle: { backgroundColor: colors.canvas },
                    headerStyle: { backgroundColor: colors.canvas },
                    headerTintColor: colors.ink,
                    headerShadowVisible: false,
                  }}>
                    <Stack.Screen name="(tabs)" />
                    <Stack.Screen name="login" />
                    <Stack.Screen name="register" />
                    <Stack.Screen name="case/[id]" options={{ headerShown: true, title: "" }} />
                  </Stack>
                </>
              )}
            </ThemeProvider>
          </LanguageProvider>
        </AuthProvider>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
