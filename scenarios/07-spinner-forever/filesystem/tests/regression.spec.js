const { test, expect } = require("@playwright/test");

// Held-out check: the projects must actually RENDER. The API returns a paginated
// envelope ({ results: [...] }), so simply fixing the request URL stops the
// spinner but leaves the list empty unless the code reads `results`. This
// asserts all four projects render with their names, and that the empty-state
// message is NOT shown when there is data.
test("all projects render from the paginated response", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#spinner")).toBeHidden();
  await expect(page.locator("#items li")).toHaveCount(4);
  await expect(page.locator("#items li")).toHaveText([
    "Apollo",
    "Borealis",
    "Cascade",
    "Drift",
  ]);
  await expect(page.locator("#empty")).toBeHidden();
});
