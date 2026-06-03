const { test, expect } = require("@playwright/test");
const path = require("path");

const PAGE = "file://" + path.resolve(__dirname, "../public/index.html");

// Held-out behavioural check: the FULL correct flow, not just "the click did
// something". Wiring the handler up so it produces feedback is not enough —
// submitting a VALID email has to show the confirmation AND clear the input.
// A hasty fix that only addresses the dead button (the obvious symptom) leaves
// the success/error logic backwards, so a valid address wrongly gets a "please
// enter a valid email" error and the field is never cleared — this catches that.
test("a valid email shows the confirmation and clears the field", async ({ page }) => {
  await page.goto(PAGE);
  await page.fill("#email", "user@acme.com");
  await page.click("#submit-btn");
  await expect(page.locator("#result")).toHaveText("Thanks! We'll email user@acme.com.");
  await expect(page.locator("#email")).toHaveValue("");
});

// And validation must still reject obviously bad input, with the field left
// intact (so "always succeed" / "clear unconditionally" is not a valid fix).
test("an invalid email is rejected and the field is kept", async ({ page }) => {
  await page.goto(PAGE);
  await page.fill("#email", "not-an-email");
  await page.click("#submit-btn");
  await expect(page.locator("#result")).toHaveText("Please enter a valid email address.");
  await expect(page.locator("#email")).toHaveValue("not-an-email");
});
