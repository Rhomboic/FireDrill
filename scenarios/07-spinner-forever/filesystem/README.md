# acme-dashboard

The customer dashboard (`public/`). It fetches the user's projects and renders
them. The projects API responds with a paginated envelope; the mock response is
served from `public/data/items.json`.

## Test

```
playwright test
```
