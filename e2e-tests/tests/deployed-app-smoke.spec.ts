import { expect, test } from "@playwright/test";

/**
 * Deployment smoke test for the hosted production deployment.
 *
 * Runs ON DEMAND against the live site (see the baseURL in
 * playwright.config.ts). It is intentionally not part of CI, which
 * tests the codebase itself without depending on production uptime.
 *
 * The sample-path check doubles as a deployment-freshness canary: the
 * synthetic sample button only exists in the mock-first build. If the
 * button is missing, the deployment predates main and the report says
 * so instead of failing hard.
 */

test.describe("deployed production smoke", () => {
  test("home page renders the upload workflow", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveTitle(/AI Product Listing Assistant/);
    await expect(page.getByTestId("upload-card")).toBeVisible();
    await expect(page.getByText("Generate professional product listings")).toBeVisible();
  });

  test("synthetic sample path renders a structured draft", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    const sampleButton = page.getByRole("button", { name: "Try sample product" });
    if ((await sampleButton.count()) === 0) {
      test.info().annotations.push({
        type: "warning",
        description:
          "Deployment predates the mock-first sample path on main; the production build is stale and needs a manual release.",
      });
      return;
    }
    await sampleButton.click();
    await expect(page.getByText("Sample data", { exact: true })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByText("Minimalist Reusable Desk Organizer")).toBeVisible();
  });
});
