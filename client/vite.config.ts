import { defineConfig } from "vite";

export default defineConfig({
  server: {
    // Same origin for the page and the bot: the runner on 7860 answers /api.
    proxy: { "/api": "http://localhost:7860" },
  },
});
