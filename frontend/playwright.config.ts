import { defineConfig, devices } from '@playwright/test'

// End-to-end tests run the real React app in a browser, with /api mocked in
// each test, so they need neither the backend nor the bank.
export default defineConfig({
  testDir: 'e2e',
  // Not *.test.ts, so Vitest leaves these to Playwright.
  testMatch: '*.e2e.ts',
  use: { baseURL: 'http://localhost:5173' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
  },
})
