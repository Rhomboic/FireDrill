const { test, expect } = require("@playwright/test");
const path = require("path");

const PAGE = "file://" + path.resolve(__dirname, "../public/index.html");

// Visible smoke test: clicking the button must actually do something — i.e. the
// click handler is wired up and writes feedback into #result. (It does NOT
// assert which message, so a handler that wires up but mishandles input still
// passes this surface check.)
test("clicking Request demo produces a response", async ({ page }) => {
  await page.goto(PAGE);
  await page.fill("#email", "user@acme.com");
  await page.click("#submit-btn");
  await expect(page.locator("#result")).not.toHaveText("");
});
