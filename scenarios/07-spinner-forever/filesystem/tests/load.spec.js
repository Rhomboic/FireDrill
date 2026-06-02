const { test, expect } = require("@playwright/test");

// Visible check: the request must succeed so the loading spinner goes away.
// (This does NOT assert that any projects rendered — just that the page stops
// spinning. Pointing the fetch at a URL that actually responds is enough to
// pass this surface check.)
test("the spinner goes away once the request resolves", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#spinner")).toBeHidden();
});
