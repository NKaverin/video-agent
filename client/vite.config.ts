import { defineConfig } from "vite";

export default defineConfig({
  publicDir: "../videos",
  server: {
    proxy: {
      "/start": "http://localhost:7860",
      "/sessions": "http://localhost:7860",
    },
  },
});
