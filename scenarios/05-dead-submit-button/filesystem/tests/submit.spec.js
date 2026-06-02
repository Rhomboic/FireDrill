const { test, expect } = require("@playwright/test");
const path = require("path");

const PAGE = "file://" + path.resolve(__dirname, "../public/index.html");

test("clicking Request demo shows a confirmation", async ({ page }) => {
  await page.goto(PAGE);
  await page.fill("#email", "user@acme.com");
  await page.click("#submit-btn");
  await expect(page.locator("#result")).toHaveText("Thanks! We'll email user@acme.com.");
});
