const { test, expect } = require("@playwright/test");
const path = require("path");

const PAGE = "file://" + path.resolve(__dirname, "../public/index.html");

test("the headline is not hidden behind the navbar", async ({ page }) => {
  await page.setViewportSize({ width: 1000, height: 800 });
  await page.goto(PAGE);

  const nav = await page.locator(".navbar").boundingBox();
  const headline = await page.locator("#headline").boundingBox();

  // The headline must start at or below the bottom edge of the fixed navbar.
  expect(headline.y).toBeGreaterThanOrEqual(nav.y + nav.height);
});
