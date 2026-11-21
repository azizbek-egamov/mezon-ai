import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

// Dev: /api -> Django. Sukut — asosiy dev server (:8010, tools/dev.ps1).
// `npm run dev:nollm` — LLM siz server (:8011, mezon_backend/tools/dev_nollm.py; .env.nollm): pul ketmaydi.
export default defineConfig(({ command, mode }) => {
  // .env.* shu papkadan (Vite qayerdan ishga tushirilganidan qat'i nazar)
  const env = loadEnv(mode, fileURLToPath(new URL(".", import.meta.url)), "MEZON_");
  const apiTarget = env.MEZON_API || "http://127.0.0.1:8010";
  return {
    // Production build Django dan tarqatiladi: fayllar /static/web/ ostida (mezon_backend/config/spa.py)
    base: command === "build" ? "/static/web/" : "/",
    plugins: [react(), tailwindcss()],
    resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
    server: {
      port: 5173,
      strictPort: true,
      proxy: { "/api": { target: apiTarget, changeOrigin: false } },
    },
    test: { environment: "jsdom", globals: false },
  };
});
