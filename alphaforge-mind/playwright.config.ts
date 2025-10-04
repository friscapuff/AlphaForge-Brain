import { defineConfig, devices } from '@playwright/test';

// T056: Initial visual regression scaffolding.
// NOTE: This is a minimal config; actual visual baseline capture will be gated
// until charts have deterministic rendering in CI (fonts + timezone stable).
export default defineConfig({
  testDir: './tests/visual',
  timeout: 30_000,
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure'
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ]
});
