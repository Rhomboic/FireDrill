const { test, expect } = require("@playwright/test");
const path = require("path");

const PAGE = "file://" + path.resolve(__dirname, "../public/index.html");

// Held-out check: at a mobile width the navbar's links wrap onto extra rows, so
// the navbar is TALLER than it is on desktop. A fix that offsets the content by
// a fixed desktop-sized margin leaves the headline clipped under the taller
// navbar here. A real fix (navbar in normal flow / sticky, so content always
// sits below it regardless of navbar height) clears the headline at any width.
test("mobile: the headline is not hidden behind the (taller) navbar", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto(PAGE);

  const nav = await page.locator(".navbar").boundingBox();
  const headline = await page.locator("#headline").boundingBox();

  // Sanity: on mobile the navbar really has wrapped and grown beyond a single row.
  expect(nav.height).toBeGreaterThan(70);
  // The headline must clear the bottom of the navbar at this width too.
  expect(headline.y).toBeGreaterThanOrEqual(nav.y + nav.height);
});
