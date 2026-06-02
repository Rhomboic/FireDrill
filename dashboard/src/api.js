// Where the result JSONs live. Local dev reads /results/ (served from public/);
// the deployed site reads the public S3 bucket. Override with ?base=<url>.
const IS_LOCAL = ["localhost", "127.0.0.1", "::1", ""].includes(location.hostname);
const params = new URLSearchParams(location.search);

export const RESULTS_BASE =
  params.get("base") ||
  (IS_LOCAL
    ? "/results/"
    : "https://firedrill-results-673981388599.s3.us-west-1.amazonaws.com/runs/");

// Load the manifest ({ model: [scenario, ...] }) then every per-job JSON.
export async function loadResults() {
  const res = await fetch(RESULTS_BASE + "manifest.json", { cache: "no-store" });
  if (!res.ok) throw new Error(`manifest.json ${res.status}`);
  const manifest = await res.json();

  const jobs = [];
  await Promise.all(
    Object.entries(manifest).flatMap(([model, scenarios]) =>
      (scenarios || []).map(async (scenario) => {
        try {
          const r = await fetch(`${RESULTS_BASE}${model}/${scenario}.json`, { cache: "no-store" });
          if (r.ok) {
            const job = await r.json();
            // Stable matrix keys from the manifest (job.scenario is the friendly
            // name; _scenario is the directory id used in S3 paths).
            job._scenario = scenario;
            job._model = model;
            jobs.push(job);
          }
        } catch {
          /* skip a missing/failed job */
        }
      })
    )
  );
  return jobs;
}
