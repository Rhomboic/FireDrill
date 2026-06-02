// Wire up the demo-request form: on submit, show a confirmation message.

const btn = document.getElementById("submitBtn");
btn.addEventListener("click", () => {
  const email = document.getElementById("email").value;
  document.getElementById("result").textContent = `Thanks! We'll email ${email}.`;
});
