import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import istanbul from "vite-plugin-istanbul";

// The backend runs on :8000; proxy API and health calls to it in development so the
// frontend can be served from :5173 without CORS friction. Set COVERAGE=1 to instrument
// the sources for the end-to-end coverage report.
export default defineConfig({
  plugins: [
    react(),
    ...(process.env.COVERAGE
      ? [istanbul({ include: "src/*", extension: [".ts", ".tsx"], requireEnv: false })]
      : []),
  ],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
