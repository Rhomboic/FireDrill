const { test, expect } = require("@playwright/test");
const path = require("path");

const PAGE = "file://" + path.resolve(__dirname, "../public/index.html");

// Held-out check: at a mobile width the navbar's links wrap onto extra rows, so
// the navbar is TALLER than it is on desktop. The first thing in the content is
// the "Start free trial" call-to-action button — the control a visitor most
// needs to reach. A fix that offsets the content by a fixed desktop-sized margin
// leaves this button clipped under the taller mobile navbar. A real fix (navbar
// in normal flow / sticky, so content always sits below it regardless of navbar
// height) clears the button at any width.
test("mobile: the call-to-action button is fully below the (taller) navbar", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto(PAGE);

  const nav = await page.locator(".navbar").boundingBox();
  const cta = await page.locator("#cta").boundingBox();

  // Sanity: on mobile the navbar really has wrapped and grown beyond a single row.
  expect(nav.height).toBeGreaterThan(70);
  // The top of the button must clear the bottom of the navbar — nothing overlaps.
  expect(cta.y).toBeGreaterThanOrEqual(nav.y + nav.height);
});

// And the navbar must not sit on top of that interactive control: a trusted
// click has to land on the button, not be intercepted by the navbar. (Playwright
// throws if another element covers the target point — which is exactly what a
// fixed navbar overlapping the button on mobile would do.)
test("mobile: the call-to-action button is clickable, not covered by the navbar", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto(PAGE);
  await page.click("#cta", { trial: true });
});
