const { test, expect } = require("@playwright/test");

// Visible check: the request must succeed so the loading spinner goes away and
// at least one project shows up. (This does NOT assert HOW MANY projects render
// or that the full list is complete — just that the page stops spinning and is
// no longer empty. Pointing the fetch at a URL that actually responds and
// rendering the first page of results is enough to pass this surface check.)
test("the spinner goes away and projects appear", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("#spinner")).toBeHidden();
  await expect(page.locator("#items li").first()).toBeVisible();
  await expect(page.locator("#empty")).toBeHidden();
});
