// Wire up the demo-request form: on submit, validate the email, then either
// show a confirmation (and clear the field) or show a validation error.

const btn = document.getElementById("submitBtn");

function isValidEmail(value) {
  // An email is valid when it has a non-empty local part, an "@", and a
  // dot-separated domain. Reject anything that doesn't match.
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value);
}

btn.addEventListener("click", () => {
  const input = document.getElementById("email");
  const result = document.getElementById("result");
  const email = input.value.trim();

  // BUG: this rejects valid addresses — the `!` is on the wrong side, so the
  // "invalid email" branch fires for *valid* input and the success branch
  // never runs (the field is never cleared and no confirmation appears).
  if (isValidEmail(email)) {
    result.textContent = "Please enter a valid email address.";
    return;
  }

  result.textContent = `Thanks! We'll email ${email}.`;
  input.value = "";
});
