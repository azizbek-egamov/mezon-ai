#!/usr/bin/env node
/**
 * Metro (dev build uchun JS bundle) — telefon `adb reverse tcp:8081` orqali ulanadi:
 *   node apps/mobile/scripts/dev-metro.js [port]
 * Expo loyiha ildizini process.cwd() dan qidiradi — avval ilova papkasiga o'tamiz.
 */
const path = require("node:path");

process.chdir(path.resolve(__dirname, ".."));
const port = process.argv[2] ?? "8081";
process.argv = [process.argv[0], require.resolve("expo/bin/cli"), "start", "--port", port, "--localhost"];
require("expo/bin/cli");
