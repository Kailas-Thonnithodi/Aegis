import { defineConfig, devices } from "@playwright/test";

const backend = "http://localhost:8001";

export default defineConfig({
  testDir: "e2e",
  workers: 1,
  use: { baseURL: "http://localhost:5174" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command:
        "uv run -m backend.seed && uv run -m uvicorn backend.main:app --port 8001",
      url: `${backend}/api/health`,
      reuseExistingServer: false,
      env: {
        AEGIS_DB: "e2e.db",
        AEGIS_CHECK_DB: "e2e-checks.db",
        MODEL_NAME: "stub",
        BACKEND_URL: backend,
      },
    },
    {
      command: "npx vite dashboard --port 5174 --strictPort",
      url: "http://localhost:5174",
      reuseExistingServer: false,
      env: { BACKEND_URL: backend },
    },
  ],
});
