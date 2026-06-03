# acme-dashboard

The customer dashboard (`public/`). It fetches the user's projects and renders
them. The projects API responds with a cursor-paginated envelope (each page
carries a `next` link to the following page); the mock responses are served from
`public/data/items*.json`, starting at `public/data/items.json`.

## Test

```
playwright test
```
