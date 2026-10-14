import { defineConfig, devices } from "@playwright/test";
import { loadEnv } from "vite";

// The E2E suite runs the real API wired to the offline demo client, so scores are
// deterministic and no model or API key is needed. Ports come from BACKEND_PORT and
// FRONTEND_PORT (environment or frontend/.env), the same variables the dev server reads.
const env = { ...loadEnv("development", process.cwd(), ""), ...process.env };
const backendPort = env.BACKEND_PORT || "8000";
const frontendUrl = `http://localhost:${env.FRONTEND_PORT || "5173"}`;

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 1,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: frontendUrl,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // A throwaway overlay keeps model add/remove in the suite from touching the
      // real gitignored models.runtime.yaml the dev server uses. OPENAI_API_KEY is
      // cleared so the credential test starts from a known "no key" state.
      command:
        `OPENAI_API_KEY= WORKSHOP_EVALS_FAKE_LLM=1 WORKSHOP_EVALS_MODELS_OVERLAY=.e2e-overlay.yaml WORKSHOP_EVALS_DATASETS_OVERLAY=.e2e-datasets.json ../backend/.venv/bin/uvicorn workshop_evals.adapters.inbound.http.app:app --host 127.0.0.1 --port ${backendPort}`,
      url: `http://127.0.0.1:${backendPort}/health`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: "COVERAGE=1 npm run dev",
      url: frontendUrl,
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
