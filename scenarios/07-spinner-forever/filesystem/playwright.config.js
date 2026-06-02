module.exports = {
  testDir: "./tests",
  reporter: "line",
  use: { headless: true, baseURL: "http://localhost:8099" },
  // Serve public/ so the page and its data are reachable over http (file:// can't fetch).
  webServer: {
    command: "python3 -m http.server 8099 --directory public",
    url: "http://localhost:8099",
    reuseExistingServer: false,
    timeout: 20000,
  },
};
