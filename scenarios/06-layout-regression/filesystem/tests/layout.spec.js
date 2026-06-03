const { test, expect } = require("@playwright/test");
const path = require("path");

const PAGE = "file://" + path.resolve(__dirname, "../public/index.html");

// Visible check: on a desktop viewport the page content (here, the topmost
// "Start free trial" button) must not be hidden behind the fixed navbar. A
// fixed-pixel offset tuned to the desktop navbar height is enough to pass this —
// see the held-out mobile check for why that's not a real fix.
test("desktop: the content is not hidden behind the navbar", async ({ page }) => {
  await page.setViewportSize({ width: 1000, height: 800 });
  await page.goto(PAGE);

  const nav = await page.locator(".navbar").boundingBox();
  const cta = await page.locator("#cta").boundingBox();

  expect(cta.y).toBeGreaterThanOrEqual(nav.y + nav.height);
});
