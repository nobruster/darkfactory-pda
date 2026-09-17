import { defineConfig } from "@playwright/test";

const viewports = [
  { name: "desktop-1600", width: 1600, height: 900 },
  { name: "desktop-1280", width: 1280, height: 720 },
  { name: "tablet-1024", width: 1024, height: 768 },
  { name: "compact-768", width: 768, height: 900 },
  { name: "mobile-390", width: 390, height: 844 },
  { name: "mobile-320", width: 320, height: 720 },
];

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.spec.ts",
  outputDir: "../../output/playwright/cockpit",
  fullyParallel: false,
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  timeout: 30_000,
  expect: {
    timeout: 8_000,
  },
  reporter: process.env.CI
    ? [
        ["line"],
        [
          "html",
          { open: "never", outputFolder: "../../output/playwright/cockpit-report" },
        ],
      ]
    : "line",
  use: {
    baseURL: "http://127.0.0.1:4274",
    colorScheme: "dark",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
  },
  projects: viewports.map(({ name, width, height }) => ({
    name,
    use: { viewport: { width, height } },
  })),
  webServer: {
    command:
      "npm run build && npm run start -- --cvg-home ../.. --project-root e2e/fixtures/workspace --port 4274",
    cwd: ".",
    url: "http://127.0.0.1:4274/api/health",
    // CI always builds and starts its own server. Locally, reusing one that is
    // already listening keeps a crashed or interrupted run from leaving the port
    // squatted, which otherwise fails every later run before a single test runs.
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
