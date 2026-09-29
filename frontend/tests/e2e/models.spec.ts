import { expect, test } from "./fixtures";

const openModelsTab = async (page: import("@playwright/test").Page) => {
  await page.goto("/");
  await page.locator(".tabs").getByRole("button", { name: "Models" }).click();
};

const mockDiscover = (page: import("@playwright/test").Page, body: unknown) =>
  page.route("**/api/catalog/discover", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) }),
  );

test("models: lists the catalogue with sources and key status", async ({ page }) => {
  await openModelsTab(page);
  await expect(page.getByText("Discover local models")).toBeVisible();

  const qwen = page.locator("tr", { hasText: "Qwen3 4B (local)" });
  await expect(qwen).toBeVisible();
  await expect(qwen.locator(".chip", { hasText: "file" })).toBeVisible();
  await expect(qwen.locator(".chip", { hasText: "not needed" })).toBeVisible();

  // A remote model with no key set shows as missing.
  const gpt = page.locator("tr", { hasText: "GPT-4o Mini" });
  await expect(gpt.locator(".chip", { hasText: "no key" })).toBeVisible();
});

test("models: discovers a local server and adds one of its models", async ({ page }) => {
  await mockDiscover(page, { models: ["qwen3:4b", "phi4:latest"], already_added: ["qwen3:4b"] });
  await openModelsTab(page);
  await page.getByRole("button", { name: "Discover models" }).click();

  // qwen3:4b is already in the file catalogue; phi4 is offered to add.
  const known = page.locator(".check", { hasText: "qwen3:4b" });
  await expect(known.locator(".chip", { hasText: "added" })).toBeVisible();

  const fresh = page.locator(".check", { hasText: "phi4:latest" });
  await fresh.getByRole("button", { name: "Add", exact: true }).click();
  await expect(fresh.locator(".chip", { hasText: "added" })).toBeVisible();

  const row = page.locator("tr", { hasText: "phi4:latest (local)" });
  await expect(row.locator(".chip", { hasText: "user" })).toBeVisible();

  // Clean up so the catalogue ends as it started.
  await row.getByRole("button", { name: "Remove" }).click();
  await expect(page.locator("tr", { hasText: "phi4:latest (local)" })).toHaveCount(0);
});

test("models: discovery reports when nothing is served", async ({ page }) => {
  await mockDiscover(page, { models: [], already_added: [] });
  await openModelsTab(page);
  await page.getByRole("button", { name: "Discover models" }).click();
  await expect(page.getByText("The server reported no models.")).toBeVisible();
});

test("models: surfaces a discovery error", async ({ page }) => {
  await page.route("**/api/catalog/discover", (route) =>
    route.fulfill({
      status: 502,
      contentType: "application/json",
      body: JSON.stringify({ detail: "could not reach http://nope" }),
    }),
  );
  await openModelsTab(page);
  await page.getByRole("button", { name: "Discover models" }).click();
  await expect(page.locator(".banner")).toContainText("could not reach");
});

test("models: adds, edits, and removes a model by hand", async ({ page }) => {
  await openModelsTab(page);

  await page.getByLabel("Catalogue id").fill("e2e-temp");
  await page.getByLabel("Display name").fill("E2E Temp");
  await page.getByLabel("Provider model id").fill("e2e:1b");
  await page.getByLabel("Base URL", { exact: true }).fill("http://localhost:11434/v1");
  await page.getByLabel("Role").selectOption("candidate");
  await page.getByLabel("Reasoning model").check();
  await page.getByRole("button", { name: "Add model" }).click();
  await expect(
    page.locator("tr", { hasText: "E2E Temp" }).locator(".chip", { hasText: "user" }),
  ).toBeVisible();

  // The new model reaches the other tabs' selectors (the refresh wiring).
  await page.locator(".tabs").getByRole("button", { name: "Playground" }).click();
  await expect(page.getByLabel("Candidate model")).toContainText("E2E Temp");
  await page.locator(".tabs").getByRole("button", { name: "Models" }).click();

  // Edit: the form populates, the id is locked, and Cancel resets it.
  await page.locator("tr", { hasText: "E2E Temp" }).getByRole("button", { name: "Edit" }).click();
  await expect(page.getByText("Edit e2e-temp")).toBeVisible();
  await expect(page.getByLabel("Catalogue id")).toBeDisabled();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByText("Add a model")).toBeVisible();

  // Edit again and rename.
  await page.locator("tr", { hasText: "E2E Temp" }).getByRole("button", { name: "Edit" }).click();
  await page.getByLabel("Display name").fill("E2E Renamed");
  await page.getByRole("button", { name: "Save changes" }).click();
  const renamed = page.locator("tr", { hasText: "E2E Renamed" });
  await expect(renamed).toBeVisible();

  // Disable (round-trips through the API), then remove — the catalogue ends clean.
  const toggle = renamed.locator('input[type="checkbox"]');
  await toggle.click();
  await expect(toggle).not.toBeChecked();
  await renamed.getByRole("button", { name: "Remove" }).click();
  await expect(page.locator("tr", { hasText: "E2E Renamed" })).toHaveCount(0);
});

test("models: credentials surface the key variables the catalogue needs (any provider)", async ({
  page,
}) => {
  await openModelsTab(page);
  // The shipped catalogue has both OpenAI and Anthropic models — both key vars are listed,
  // not just OpenAI. Proves the credentials UI is provider-agnostic.
  const creds = page.locator(".card", { hasText: "Session credentials" });
  await expect(creds.getByText("OPENAI_API_KEY", { exact: true })).toBeVisible();
  await expect(creds.getByText("ANTHROPIC_API_KEY", { exact: true })).toBeVisible();
  // Clicking one prefills the key-variable field.
  await creds.getByText("ANTHROPIC_API_KEY", { exact: true }).click();
  await expect(page.getByLabel("Key variable", { exact: true })).toHaveValue("ANTHROPIC_API_KEY");
});

test("models: rejects a non-key variable and accepts a real one", async ({ page }) => {
  await openModelsTab(page);

  // A variable that is neither a key nor referenced by a model is refused.
  await page.getByLabel("Key variable", { exact: true }).fill("HOME");
  await page.getByLabel("Value").fill("x");
  await page.getByRole("button", { name: "Set for this session" }).click();
  await expect(page.locator(".banner")).toContainText("not an accepted key variable");

  // A real key variable is accepted, and the remote models pick it up.
  await page.getByLabel("Key variable", { exact: true }).fill("OPENAI_API_KEY");
  await page.getByLabel("Value").fill("sk-test-dummy");
  await page.getByRole("button", { name: "Set for this session" }).click();
  await expect(page.locator(".chip", { hasText: "set for this session" })).toBeVisible();

  const gpt = page.locator("tr", { hasText: "GPT-4o Mini" });
  await expect(gpt.locator(".chip", { hasText: "key set" })).toBeVisible();
});
