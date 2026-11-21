/**
 * Expo konfiguratsiyasi. `MEZON_ENV=production` bo'lmasa — dev build: oddiy HTTP ruxsat (telefon ichidagi
 * http://localhost:8010 → `adb reverse` → PC dagi Django). Production — faqat HTTPS (Cloudflare Tunnel, 17-bosqich).
 */
import type { ConfigContext, ExpoConfig } from "expo/config";

const production = process.env.MEZON_ENV === "production";

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "MEZON AI",
  slug: "mezon-ai",
  version: "0.1.0",
  orientation: "portrait",
  icon: "./assets/images/icon.png",
  scheme: "mezon",
  userInterfaceStyle: "automatic",   // yorug'/qorong'i ilova ichida tanlanadi (Klassik dizayn); tizim elementlari moslashadi
  backgroundColor: "#F7F4EC",
  android: {
    package: "uz.mezon.app",
    adaptiveIcon: {
      backgroundColor: "#121824",
      foregroundImage: "./assets/images/android-icon-foreground.png",
      backgroundImage: "./assets/images/android-icon-background.png",
      monochromeImage: "./assets/images/android-icon-monochrome.png",
    },
    predictiveBackGestureEnabled: false,
    // Android zaxira nusxasiga (Google Drive) ilova ma'lumotlari tushmasin — advokatlik siri
    allowBackup: false,
  },
  web: { output: "single", favicon: "./assets/images/favicon.png" },
  plugins: [
    "expo-router",
    "expo-secure-store",
    "expo-localization",
    [
      "expo-image-picker",
      {
        cameraPermission: "Ish hujjatlarini suratga olish uchun MEZON AI kameradan foydalanadi.",
        photosPermission: "Ish hujjatlari rasmlarini tanlash uchun MEZON AI galereyadan foydalanadi.",
        microphonePermission: false,
      },
    ],
    ["expo-build-properties", { android: { usesCleartextTraffic: !production } }],
    [
      "expo-splash-screen",
      { backgroundColor: "#0B0F17", image: "./assets/images/splash-icon.png", imageWidth: 96 },
    ],
    "./plugins/withReleaseSigning", // release APK — credentials/ dagi o'z kalitimiz bilan
  ],
  experiments: { typedRoutes: true, reactCompiler: true },
});
