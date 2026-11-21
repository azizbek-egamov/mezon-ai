/**
 * Kichik maxfiy qiymatlar (refresh token, til): telefonda — expo-secure-store (Android Keystore bilan shifrlangan),
 * veb-rejimda (faqat dev ko'rinish uchun) — sessionStorage.
 */
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

const web = Platform.OS === "web";

export const storage = {
  async get(key: string): Promise<string | null> {
    if (web) return globalThis.sessionStorage?.getItem(key) ?? null;
    return SecureStore.getItemAsync(key);
  },
  async set(key: string, value: string): Promise<void> {
    if (web) return void globalThis.sessionStorage?.setItem(key, value);
    await SecureStore.setItemAsync(key, value);
  },
  async remove(key: string): Promise<void> {
    if (web) return void globalThis.sessionStorage?.removeItem(key);
    await SecureStore.deleteItemAsync(key);
  },
};
