const { test, expect } = require("@playwright/test");
const path = require("path");

const PAGE = "file://" + path.resolve(__dirname, "../public/index.html");

// Held-out behavioural check: a VALID submission must actually succeed.
// Wiring the handler up is not enough — submitting a valid email has to show the
// confirmation AND clear the input. (A naive id-only fix leaves an inverted
// validation check, so valid input wrongly gets a "please enter a valid email"
// error and the field is never cleared — this catches that.)
test("a valid email shows the confirmation and clears the field", async ({ page }) => {
  await page.goto(PAGE);
  await page.fill("#email", "user@acme.com");
  await page.click("#submit-btn");
  await expect(page.locator("#result")).toHaveText("Thanks! We'll email user@acme.com.");
  await expect(page.locator("#email")).toHaveValue("");
});

// And validation must still reject obviously bad input (so "always succeed" is
// not a valid fix either).
test("an invalid email is rejected", async ({ page }) => {
  await page.goto(PAGE);
  await page.fill("#email", "not-an-email");
  await page.click("#submit-btn");
  await expect(page.locator("#result")).toHaveText("Please enter a valid email address.");
});
