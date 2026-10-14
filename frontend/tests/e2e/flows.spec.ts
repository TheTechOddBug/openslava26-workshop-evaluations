import { expect, test } from "./fixtures";

const modelResponse = (page: import("@playwright/test").Page) =>
  page.locator(".card", { hasText: "Model response" }).locator(".response");

test("playground: one mechanism scores a sentiment case", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Category").selectOption("sentiment_classification");
  await expect(page.getByLabel("Case")).toContainText("sent-01");
  await page.waitForLoadState("networkidle"); // let the applicability fetch settle

  const exact = page.locator(".check", { hasText: "Exact match" }).locator("input");
  await expect(exact).toBeEnabled();
  await exact.check();

  await page.getByRole("button", { name: "Evaluate" }).click();
  await expect(modelResponse(page)).toContainText("positive");
  await expect(page.locator(".score-card")).toHaveCount(1);
});

test("playground: several mechanisms score the same response", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Category").selectOption("sentiment_classification");
  await expect(page.getByLabel("Case")).toContainText("sent-01");
  await page.waitForLoadState("networkidle"); // let the applicability fetch settle

  await page.locator(".check", { hasText: "Exact match" }).locator("input").check();
  await page.locator(".check", { hasText: "LLM as judge" }).locator("input").check();
  await expect(page.getByLabel("Judge model")).toBeVisible();
  await expect(page.getByRole("button", { name: "Evaluate" })).toBeEnabled();

  await page.getByRole("button", { name: "Evaluate" }).click();
  await expect(page.locator(".score-card")).toHaveCount(2, { timeout: 15_000 });
  await expect(page.locator(".dims").first()).toBeVisible(); // judge dimensions render
});

test("playground: mechanisms needing absent fields are disabled", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Category").selectOption("sentiment_classification");
  await expect(page.getByLabel("Case")).toContainText("sent-01");
  await page.waitForLoadState("networkidle"); // let the applicability fetch settle

  await expect(page.locator(".check", { hasText: "JSON schema" }).locator("input")).toBeDisabled();
  await expect(page.locator(".check", { hasText: "Code execution" }).locator("input")).toBeDisabled();
  await expect(page.locator(".check", { hasText: "Exact match" }).locator("input")).toBeEnabled();
});

test("playground: custom prompt with a reference", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Custom" }).click();
  await page.getByLabel("Prompt").fill("Say the word positive.");
  await page.getByLabel("Reference answer (optional)").fill("positive");
  await page.locator(".check", { hasText: "Exact match" }).locator("input").check();
  await page.getByRole("button", { name: "Evaluate" }).click();
  await expect(modelResponse(page)).toContainText("positive");
});

test("playground: adjusts model parameters including reasoning", async ({ page }) => {
  await page.goto("/");
  // The default candidate (Qwen3 4B) declares reasoning support, so its control shows.
  await expect(page.getByLabel("Reasoning effort")).toBeVisible();
  await page.getByLabel("Reasoning effort").selectOption("high");
  await page.getByLabel("Max tokens").fill("256");
  await page.locator('input[type="range"]').fill("0.7");
  await expect(page.getByText(/Temperature: 0\.70/)).toBeVisible();
});

test("matrix: adds and removes a candidate", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Matrix" }).click();
  await expect(page.getByTitle("Remove")).toHaveCount(0); // one candidate, no remove control

  await page.getByRole("button", { name: "Add candidate" }).click();
  await expect(page.getByTitle("Remove")).toHaveCount(2);

  await page.getByTitle("Remove").last().click();
  await expect(page.getByTitle("Remove")).toHaveCount(0);
});

test("matrix: toggling cases and mechanisms updates the selection", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Matrix" }).click();
  await page.getByLabel("Category").selectOption("sentiment_classification");

  const firstCase = page.locator(".card", { hasText: "Cases" }).locator(".check input").first();
  await firstCase.uncheck();
  await firstCase.check();

  const judge = page.locator(".check", { hasText: "LLM as judge" }).locator("input");
  await judge.check();
  await expect(page.getByLabel("Judge model")).toBeVisible();
  await judge.uncheck();
});

test("matrix: runs cases against candidates and fills the grid", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Matrix" }).click();
  await page.getByLabel("Category").selectOption("sentiment_classification");
  await page.getByRole("button", { name: "Run matrix" }).click();

  await expect(page.getByText(/Results — completed/)).toBeVisible({ timeout: 30_000 });
  await expect(page.locator(".matrix table")).toBeVisible();
  await expect(page.locator(".cell-scores").first()).toBeVisible();
  // token usage per cell and a per-column total
  await expect(page.locator(".cell-scores .cell-usage").first()).toHaveText(/\d+ in · \d+ out/);
  await expect(page.locator(".matrix tfoot")).toContainText("Tokens");
  await expect(page.locator(".matrix tfoot .cell-usage--total")).toHaveText(/\d+ in · \d+ out/);
});

test("matrix: the gate blocks below the threshold and passes when it is lowered", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Matrix" }).click();
  await page.getByLabel("Category").selectOption("sentiment_classification");
  await page.waitForLoadState("networkidle");
  await page.getByRole("button", { name: "Run matrix" }).click();
  await expect(page.getByText(/Results — completed/)).toBeVisible({ timeout: 30_000 });

  // demo answers are always "positive": 1 of the 3 default cases passes, mean 0.33
  const gate = page.locator(".matrix tfoot .gate-row");
  await expect(gate.locator(".gate-verdict")).toHaveText("BLOCKED");
  await expect(gate).toContainText("exact_match 0.33 < 0.90");

  await page.getByLabel("exact_match threshold").fill("0.3");
  await expect(gate.locator(".gate-verdict")).toHaveText("PASS");
  await expect(gate).toContainText("exact_match 0.33 ≥ 0.30");
});

test("matrix: two prompt variants become two columns", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Matrix" }).click();
  await page.getByLabel("Category").selectOption("sentiment_classification");

  await page.getByRole("button", { name: "Add candidate" }).click();
  const overrides = page.getByPlaceholder("Replace the case prompt — e.g. a refined version");
  await expect(page.getByText("where the case's own prompt should go").first()).toBeVisible();
  await overrides.nth(1).fill("Classify strictly as positive, negative or neutral.\n\n{prompt}");

  await page.getByRole("button", { name: "Run matrix" }).click();
  await expect(page.getByText(/Results — completed/)).toBeVisible({ timeout: 30_000 });
  await expect(page.locator(".matrix thead th")).toHaveCount(3); // Case + two candidates
});

test("judge reliability: reports agreement and a verdict", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Judge reliability" }).click();
  await page.getByLabel("Dataset category").selectOption("sentiment_classification");
  await page.getByRole("button", { name: "Measure agreement" }).click();

  await expect(page.locator(".verdict")).toBeVisible({ timeout: 40_000 });
  await expect(page.getByText("Pearson r")).toBeVisible();
  await expect(page.getByText("Mean abs. error")).toBeVisible();
});

test("compare: judges A vs B and reveals position bias", async ({ page }) => {
  await page.goto("/");
  await page.locator(".tabs").getByRole("button", { name: "Compare" }).click();
  await page.getByLabel("Category").selectOption("sentiment_classification");
  await expect(page.getByLabel("Case")).toContainText("sent-01");
  await page.waitForLoadState("networkidle");

  await page.locator("button.btn--primary").click();
  await expect(page.locator(".verdict")).toContainText("Model A wins");
  await expect(page.locator(".banner")).toContainText("Position bias");
});

test("ensemble: several judges score one answer", async ({ page }) => {
  await page.goto("/");
  await page.locator(".tabs").getByRole("button", { name: "Ensemble" }).click();
  await page.getByLabel("Category").selectOption("sentiment_classification");
  await expect(page.getByLabel("Case")).toContainText("sent-01");
  await page.waitForLoadState("networkidle");

  await page.locator("button.btn--primary").click();
  await expect(page.getByText("Average score")).toBeVisible();
  await expect(page.getByText("Spread (disagreement)")).toBeVisible();
});
