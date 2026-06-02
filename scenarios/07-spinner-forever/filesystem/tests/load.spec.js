const { test, expect } = require("@playwright/test");

test("the project list loads and the spinner goes away", async ({ page }) => {
  await page.goto("/");
  // Data successfully loaded => all four items render and the spinner is hidden.
  await expect(page.locator("#items li")).toHaveCount(4);
  await expect(page.locator("#spinner")).toBeHidden();
});
