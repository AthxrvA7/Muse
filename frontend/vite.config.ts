import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The built site is served by the Muse backend at /app/ (same origin as the API), so the
// browser sends the login cookie automatically and no CORS is needed.
export default defineConfig({
  base: "/app/",
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": "/src" } },
  // framer-motion, Radix and React Router make the main bundle ~185 kB gzipped; charts load separately
  build: { chunkSizeWarningLimit: 700 },
  server: {
    // `npm run dev`: forward API calls to the backend on port 8000
    proxy: { "/api": "http://127.0.0.1:8000", "/ready": "http://127.0.0.1:8000" },
  },
});
