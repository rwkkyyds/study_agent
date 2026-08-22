import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  base: "/web/",
  plugins: [vue()],
  server: {
    proxy: {
      "/auth": "http://127.0.0.1:8100",
      "/interviews": "http://127.0.0.1:8100",
      "/question-bank": "http://127.0.0.1:8100",
      "/resumes": "http://127.0.0.1:8100",
      "/health": "http://127.0.0.1:8100",
    },
  },
  build: {
    outDir: "../app/web",
    emptyOutDir: true,
  },
});
