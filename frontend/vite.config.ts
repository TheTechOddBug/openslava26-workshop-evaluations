import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";
import istanbul from "vite-plugin-istanbul";

// The backend runs on BACKEND_PORT (default 8000); proxy API and health calls to it in
// development so the frontend can be served from FRONTEND_PORT (default 5173) without CORS
// friction. Both ports are read from the environment or frontend/.env. Set COVERAGE=1 to
// instrument the sources for the end-to-end coverage report.
export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, process.cwd(), ""), ...process.env };
  const backend = `http://localhost:${env.BACKEND_PORT || 8000}`;
  return {
    plugins: [
      react(),
      ...(env.COVERAGE
        ? [istanbul({ include: "src/*", extension: [".ts", ".tsx"], requireEnv: false })]
        : []),
    ],
    server: {
      port: Number(env.FRONTEND_PORT || 5173),
      // Fail fast rather than drifting to another port when this one is taken.
      strictPort: true,
      proxy: {
        "/api": backend,
        "/health": backend,
      },
    },
  };
});
