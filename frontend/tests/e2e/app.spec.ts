import { expect, test } from "./fixtures";

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Evaluate" })).toBeVisible();
});

test("switches between the views", async ({ page }) => {
  const tabs = page.locator(".tabs");

  await tabs.getByRole("button", { name: "Matrix" }).click();
  await expect(page.getByRole("button", { name: "Run matrix" })).toBeVisible();

  await tabs.getByRole("button", { name: "Compare" }).click();
  await expect(page.getByText("Candidate A")).toBeVisible();

  await tabs.getByRole("button", { name: "Ensemble" }).click();
  await expect(page.getByText("Panel of judges")).toBeVisible();

  await tabs.getByRole("button", { name: "Judge reliability" }).click();
  await expect(page.getByRole("button", { name: "Measure agreement" })).toBeVisible();

  await tabs.getByRole("button", { name: "Playground" }).click();
  await expect(page.getByRole("button", { name: "Evaluate" })).toBeVisible();
});

test("toggles light and dark theme", async ({ page }) => {
  const html = page.locator("html");
  const before = await html.getAttribute("data-theme");
  await page.getByTitle("Toggle light and dark").click();
  await expect(html).not.toHaveAttribute("data-theme", before ?? "");
});

test("loads the catalogue of mechanisms", async ({ page }) => {
  await expect(page.locator(".check__label", { hasText: "Exact match" })).toBeVisible();
  await expect(page.locator(".check__label", { hasText: "LLM as judge" })).toBeVisible();
  await expect(page.locator(".check__label", { hasText: "BLEU" })).toBeVisible();
});
