import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        app: resolve(import.meta.dirname, "app.html"),
        offscreen: resolve(import.meta.dirname, "offscreen.html")
      }
    }
  }
});
