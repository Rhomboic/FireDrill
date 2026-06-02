// Load the user's projects and render them. The data is served at ./data/items.json.

const API_URL = "http://localhost:3001/api/items";

async function load() {
  const list = document.getElementById("items");
  const spinner = document.getElementById("spinner");
  try {
    const res = await fetch(API_URL);
    const items = await res.json();
    spinner.style.display = "none";
    list.innerHTML = items.map((name) => `<li>${name}</li>`).join("");
  } catch (err) {
    // Request failed — the spinner stays up and nothing renders.
    console.error("failed to load projects", err);
  }
}

load();
