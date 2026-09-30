/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// В dev фронт ходит в API через тот же origin (прокси), CORS не нужен.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { "/api": "http://localhost:8088" } },
  build: {
    sourcemap: false,
    target: "es2022",
    rollupOptions: {
      output: {
        // редко меняющиеся библиотеки — отдельными чанками: браузер кэширует их между релизами
        manualChunks: {
          react: ["react", "react-dom", "react-router"],
          data: ["@tanstack/react-query"],
          forms: ["react-hook-form", "zod", "@hookform/resolvers"],
          motion: ["motion"],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["src/test/setup.ts"],
    css: false,
    coverage: {
      provider: "v8",
      include: ["src/api/**", "src/lib/**", "src/auth/**", "src/features/**/schemas.ts"],
      exclude: ["src/api/schema.d.ts", "src/api/queries.ts", "src/lib/tones.ts", "**/*.test.*"],
      thresholds: { lines: 80, functions: 80, branches: 75, statements: 80 },
    },
  },
});
