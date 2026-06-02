// Pagination helper for the search API. Pages are 1-indexed.
//
// getPage(items, page, perPage) returns the slice of `items` for the given page.

function getPage(items, page, perPage) {
  const start = page * perPage; // index of the first item on this page
  const result = [];
  for (let i = start; i < start + perPage; i++) {
    result.push(items[i]);
  }
  return result;
}

module.exports = { getPage };
