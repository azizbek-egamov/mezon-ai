import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

// Admin panel: http://localhost:5174. /api -> Django (sukut :8010; `npm run dev:nollm` — LLM siz :8011, .env.nollm)
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, fileURLToPath(new URL(".", import.meta.url)), "MEZON_");
  const apiTarget = env.MEZON_API || "http://127.0.0.1:8010";
  return {
    // Production build Django dan tarqatiladi: fayllar /static/panel/ ostida (mezon_backend/config/spa.py)
    base: command === "build" ? "/static/panel/" : "/",
    plugins: [react(), tailwindcss()],
    resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
    server: {
      port: 5174,
      strictPort: true,
      proxy: { "/api": { target: apiTarget, changeOrigin: false } },
    },
    test: { environment: "jsdom", globals: false },
  };
});
