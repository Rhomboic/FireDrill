// Load the user's projects and render them. The projects API returns a
// paginated envelope: { page, page_size, total, next, results: [{ id, name }, ...] }.

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
    // BUG: this points at a stale dev API that nothing serves, so the request
    // rejects, the catch below swallows it, and the spinner spins forever.
    const res = await fetch(API_URL);
    const data = await res.json();
    spinner.style.display = "none";
    render(data.results);
  } catch (err) {
    console.error("failed to load projects", err);
  }
}

load();
