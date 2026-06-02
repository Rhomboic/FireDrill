# search-pagination

Pagination helper for the search API. Pages are **1-indexed**: `getPage(items, 1, perPage)`
returns the first page.

## Test

```
node tests/run.js     # or: npm test
```

The suite is currently red (see `logs/`) — the first page of search results is wrong.
