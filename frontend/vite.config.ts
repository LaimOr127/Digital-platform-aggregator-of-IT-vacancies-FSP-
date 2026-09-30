import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// В dev фронт ходит в API через тот же origin (прокси), CORS не нужен.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8088" } },
  build: { sourcemap: false, target: "es2022" },
});
