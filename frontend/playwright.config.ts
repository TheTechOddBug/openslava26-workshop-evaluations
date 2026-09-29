import { defineConfig, devices } from "@playwright/test";

// The E2E suite runs the real API wired to the offline demo client, so scores are
// deterministic and no model or API key is needed.
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 60_000,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 1,
  workers: 1,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5173",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // A throwaway overlay keeps model add/remove in the suite from touching the
      // real gitignored models.runtime.yaml the dev server uses. OPENAI_API_KEY is
      // cleared so the credential test starts from a known "no key" state.
      command:
        "OPENAI_API_KEY= WORKSHOP_EVALS_FAKE_LLM=1 WORKSHOP_EVALS_MODELS_OVERLAY=.e2e-overlay.yaml WORKSHOP_EVALS_DATASETS_OVERLAY=.e2e-datasets.json ../backend/.venv/bin/uvicorn workshop_evals.adapters.inbound.http.app:app --host 127.0.0.1 --port 8000",
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: "COVERAGE=1 npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
