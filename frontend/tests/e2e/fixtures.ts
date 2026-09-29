import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";

import { test as base, expect } from "@playwright/test";

// After each test, save the istanbul coverage the instrumented app accumulated on
// window.__coverage__ so `nyc` can turn it into a report.
export const test = base.extend<{ autoCoverage: void }>({
  autoCoverage: [
    async ({ page }, use) => {
      await use();
      const coverage = await page
        .evaluate(() => (window as unknown as { __coverage__?: unknown }).__coverage__)
        .catch(() => undefined);
      if (coverage) {
        fs.mkdirSync(".nyc_output", { recursive: true });
        fs.writeFileSync(
          path.join(".nyc_output", `${crypto.randomUUID()}.json`),
          JSON.stringify(coverage),
        );
      }
    },
    { auto: true },
  ],
});

export { expect };
