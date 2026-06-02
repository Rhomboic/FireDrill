// Pagination tests. Run with: node tests/run.js
const assert = require("assert");
const { getPage } = require("../src/pagination");

// 6 items, 2 per page -> 3 full pages (no partial page in this suite).
const items = ["a", "b", "c", "d", "e", "f"];

assert.deepStrictEqual(getPage(items, 1, 2), ["a", "b"], "page 1 should be the first two items");
assert.deepStrictEqual(getPage(items, 2, 2), ["c", "d"], "page 2");
assert.deepStrictEqual(getPage(items, 3, 2), ["e", "f"], "page 3");

console.log("pagination tests passed");
