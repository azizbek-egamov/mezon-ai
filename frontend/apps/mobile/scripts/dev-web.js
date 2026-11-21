#!/usr/bin/env node
/**
 * Expo veb-rejimini (UI ni brauzerda tekshirish uchun) istalgan papkadan ishga tushirish:
 *   node apps/mobile/scripts/dev-web.js [port]
 * Expo loyiha ildizini process.cwd() dan qidiradi — shuning uchun avval ilova papkasiga o'tamiz.
 */
const path = require("node:path");

const appDir = path.resolve(__dirname, "..");
process.chdir(appDir);
const port = process.argv[2] ?? "8081";
process.argv = [process.argv[0], require.resolve("expo/bin/cli"), "start", "--web", "--port", port];
require("expo/bin/cli");
