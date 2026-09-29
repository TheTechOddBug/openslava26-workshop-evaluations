import { expect, test } from "./fixtures";

const openDatasetsTab = async (page: import("@playwright/test").Page) => {
  await page.goto("/");
  await page.locator(".tabs").getByRole("button", { name: "Datasets" }).click();
};

test("datasets: lists cases with their source; base cases can't be removed", async ({ page }) => {
  await openDatasetsTab(page);
  await page.getByLabel("Filter by category").selectOption("code_generation");

  const row = page.locator("tr", { hasText: "code-101" });
  await expect(row).toBeVisible();
  await expect(row.locator(".chip", { hasText: "file" })).toBeVisible();
  await expect(row.getByRole("button", { name: "Remove" })).toBeDisabled();
});

test("datasets: add a case, it reaches the selectors, edit it, then remove it", async ({ page }) => {
  await openDatasetsTab(page);

  await page.getByLabel("Case id").fill("e2e-ds-1");
  await page.getByLabel("Category", { exact: true }).fill("e2e-cat");
  await page.getByLabel("Prompt").fill("Reply with the word hi.");
  await page.getByLabel("Reference answer (exact / similarity)").fill("hi");
  await page.getByRole("button", { name: "Add case" }).click();

  await page.getByLabel("Filter by category").selectOption("e2e-cat");
  await expect(
    page.locator("tr", { hasText: "e2e-ds-1" }).locator(".chip", { hasText: "user" }),
  ).toBeVisible();

  // The new case reaches the other tabs' selectors (the refresh wiring).
  await page.locator(".tabs").getByRole("button", { name: "Playground" }).click();
  await page.getByRole("combobox", { name: "Category", exact: true }).selectOption("e2e-cat");
  await expect(page.getByLabel("Case")).toContainText("e2e-ds-1");

  // Edit it (id locked, prompt changed).
  await page.locator(".tabs").getByRole("button", { name: "Datasets" }).click();
  await page.getByLabel("Filter by category").selectOption("e2e-cat");
  await page.locator("tr", { hasText: "e2e-ds-1" }).getByRole("button", { name: "Edit" }).click();
  await expect(page.getByText("Edit e2e-ds-1")).toBeVisible();
  await expect(page.getByLabel("Case id")).toBeDisabled();
  await page.getByLabel("Prompt").fill("Reply with hi, please.");
  await page.getByRole("button", { name: "Save changes" }).click();

  // Disable (round-trips), then remove — the catalogue ends as it started.
  const again = page.locator("tr", { hasText: "e2e-ds-1" });
  const toggle = again.locator('input[type="checkbox"]');
  await toggle.click();
  await expect(toggle).not.toBeChecked();
  await again.getByRole("button", { name: "Remove" }).click();
  await expect(page.locator("tr", { hasText: "e2e-ds-1" })).toHaveCount(0);
});

test("datasets: the form previews which mechanisms the fields enable", async ({ page }) => {
  await openDatasetsTab(page);
  // With no reference/rubric/tests, the reference-free judge is the only mechanism.
  await expect(page.getByText(/Enables:.*LLM as judge/)).toBeVisible();
  // Adding a reference unlocks exact match / similarity.
  await page.getByLabel("Reference answer (exact / similarity)").fill("positive");
  await expect(page.getByText(/Enables:.*Exact match/)).toBeVisible();
});
