import React, { useEffect, useMemo, useState } from "react";
import { loadResults, RESULTS_BASE } from "./api.js";
import { MODEL_ORDER } from "./meta.js";
import Summary from "./components/Summary.jsx";
import Matrix from "./components/Matrix.jsx";
import Drawer from "./components/Drawer.jsx";

export default function App() {
  const [jobs, setJobs] = useState([]);
  const [status, setStatus] = useState("loading");
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    loadResults()
      .then((js) => {
        setJobs(js);
        setStatus(js.length ? "ready" : "empty");
      })
      .catch(() => setStatus("error"));
  }, []);

  // Models present (in preferred order, then any extras), and scenarios sorted.
  const { models, scenarios, cell } = useMemo(() => {
    const presentModels = new Set(jobs.map((j) => j._model));
    const models = [
      ...MODEL_ORDER.filter((m) => presentModels.has(m)),
      ...[...presentModels].filter((m) => !MODEL_ORDER.includes(m)),
    ];
    const scenarios = [...new Set(jobs.map((j) => j._scenario))].sort();
    const cell = {};
    for (const j of jobs) cell[`${j._scenario}|${j._model}`] = j;
    return { models, scenarios, cell };
  }, [jobs]);

  return (
    <>
      <header>
        <h1>🔥 FireDrill</h1>
        <p className="tagline">
          An agent gym for incident response. Each cell is one model dropped into a
          broken software project — scored on whether it fixed the incident, how
          precisely (blast radius), how well it understood it (diagnosis), and what
          it cost.
        </p>
      </header>

      <main>
        {status === "loading" && <p className="muted">Loading results…</p>}
        {status === "error" && (
          <p className="muted">
            Couldn’t load <code>{RESULTS_BASE}manifest.json</code>. Run the matrix
            first (<code>orchestrator/run_matrix.sh</code>), or check S3/CORS.
          </p>
        )}
        {status === "empty" && (
          <p className="muted">No results yet — the manifest is empty.</p>
        )}

        {status === "ready" && (
          <>
            <section>
              <h2>Models</h2>
              <p className="muted">
                Quality composite = 0.6·resolution + 0.2·blast radius + 0.2·diagnosis.
                Cost is a separate axis.
              </p>
              <Summary jobs={jobs} models={models} />
            </section>

            <section>
              <h2>Scenario × model</h2>
              <p className="muted">
                Cell = composite score (and $ cost). Click any cell for the
                transcript, diff, diagnosis and verification.
              </p>
              <Matrix
                models={models}
                scenarios={scenarios}
                cell={cell}
                onSelect={setSelected}
              />
            </section>
          </>
        )}
      </main>

      <footer className="muted">
        Results read live from S3 ·{" "}
        <a href="https://github.com/Rhomboic/FireDrill">github.com/Rhomboic/FireDrill</a>
      </footer>

      {selected && <Drawer job={selected} onClose={() => setSelected(null)} />}
    </>
  );
}
