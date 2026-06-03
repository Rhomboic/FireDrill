const { test, expect } = require("@playwright/test");

// Held-out check: ALL of the user's projects must render, not just the first
// page. The projects API is cursor-paginated — each response carries a `next`
// link and only one page of `results`. The first page holds 2 of the 6
// projects; the rest are reachable only by following `next` until it is null.
// Fixing just the request URL stops the spinner and shows the first page, but
// leaves four projects missing unless the code walks the whole cursor chain.
test("all projects render across every page of the cursor", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#spinner")).toBeHidden();
  await expect(page.locator("#items li")).toHaveCount(6);
  await expect(page.locator("#items li")).toHaveText([
    "Apollo",
    "Borealis",
    "Cascade",
    "Drift",
    "Everest",
    "Frontier",
  ]);
  await expect(page.locator("#empty")).toBeHidden();
});

// And when there is genuinely no data, the empty-state must show (so a fix can't
// just hardcode the list or ignore the empty case).
test("the empty state shows when a page has no results", async ({ page }) => {
  await page.route("**/data/items.json", (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({ page: 1, page_size: 2, total: 0, next: null, results: [] }),
    })
  );
  await page.goto("/");
  await expect(page.locator("#spinner")).toBeHidden();
  await expect(page.locator("#items li")).toHaveCount(0);
  await expect(page.locator("#empty")).toBeVisible();
});
