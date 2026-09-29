import { expect, test } from "./fixtures";

const fail = (body: Record<string, unknown> = { detail: "boom" }) => ({
  status: 500,
  contentType: "application/json",
  body: JSON.stringify(body),
});

test("shows a banner when the catalogue cannot load", async ({ page }) => {
  await page.route("**/api/catalog/**", (route) => route.fulfill(fail()));
  await page.goto("/");
  await expect(page.locator(".banner")).toBeVisible();
});

test("playground surfaces an evaluation error", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Category").selectOption("sentiment_classification");
  await expect(page.getByLabel("Case")).toContainText("sent-01");
  await page.waitForLoadState("networkidle");
  await page.locator(".check", { hasText: "Exact match" }).locator("input").check();

  await page.route("**/api/evaluate", (route) => route.fulfill(fail({ detail: "no good" })));
  await page.getByRole("button", { name: "Evaluate" }).click();
  await expect(page.locator(".banner")).toContainText("no good");
});

test("matrix surfaces a run error", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Matrix" }).click();
  await page.getByLabel("Category").selectOption("sentiment_classification");

  await page.route("**/api/runs", (route) => route.fulfill(fail({ detail: "cannot start" })));
  await page.getByRole("button", { name: "Run matrix" }).click();
  await expect(page.locator(".banner")).toContainText("cannot start");
});

test("judge reliability surfaces an error", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Judge reliability" }).click();
  await page.getByLabel("Dataset category").selectOption("sentiment_classification");

  await page.route("**/api/runs", (route) => route.fulfill(fail({ detail: "denied" })));
  await page.getByRole("button", { name: "Measure agreement" }).click();
  await expect(page.locator(".banner")).toContainText("denied");
});

test("compare surfaces an error", async ({ page }) => {
  await page.goto("/");
  await page.locator(".tabs").getByRole("button", { name: "Compare" }).click();
  await page.getByLabel("Category").selectOption("sentiment_classification");
  await expect(page.getByLabel("Case")).toContainText("sent-01");

  await page.route("**/api/compare", (route) => route.fulfill(fail({ detail: "compare failed" })));
  await page.locator("button.btn--primary").click();
  await expect(page.locator(".banner")).toContainText("compare failed");
});

test("ensemble surfaces an error", async ({ page }) => {
  await page.goto("/");
  await page.locator(".tabs").getByRole("button", { name: "Ensemble" }).click();
  await page.getByLabel("Category").selectOption("sentiment_classification");
  await expect(page.getByLabel("Case")).toContainText("sent-01");

  await page.route("**/api/ensemble-judge", (route) => route.fulfill(fail({ detail: "ensemble failed" })));
  await page.locator("button.btn--primary").click();
  await expect(page.locator(".banner")).toContainText("ensemble failed");
});
