// Load the user's projects and render them. The projects API returns a
// paginated envelope: { page, page_size, total, results: [{ id, name }, ...] }.

const API_URL = "http://localhost:3001/api/items";

function render(items) {
  const list = document.getElementById("items");
  const empty = document.getElementById("empty");
  if (!items || items.length === 0) {
    empty.style.display = "block";
    list.innerHTML = "";
    return;
  }
  empty.style.display = "none";
  list.innerHTML = items.map((p) => `<li>${p.name}</li>`).join("");
}

async function load() {
  const spinner = document.getElementById("spinner");
  try {
    const res = await fetch(API_URL);
    const data = await res.json();
    spinner.style.display = "none";
    // BUG: `data` is the paginated envelope, not the array of projects, so
    // `data.map` is undefined and this throws — nothing ever renders even once
    // the request succeeds.
    render(data.map((p) => p));
  } catch (err) {
    // Request failed (or the response shape was wrong) — the spinner is already
    // hidden above, but nothing renders.
    console.error("failed to load projects", err);
  }
}

load();
