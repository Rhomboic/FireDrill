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

  if (isValidEmail(email)) {
    result.textContent = "Please enter a valid email address.";
    return;
  }

  result.textContent = `Thanks! We'll email ${email}.`;
  input.value = "";
});
