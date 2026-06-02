import React, { useEffect, useMemo, useState } from "react";
import { loadResults, RESULTS_BASE } from "./api.js";
import { MODEL_ORDER, modelLabel } from "./meta.js";
import Overview from "./components/Overview.jsx";
import ModelTab from "./components/ModelTab.jsx";
import Drawer from "./components/Drawer.jsx";

export default function App() {
  const [jobs, setJobs] = useState([]);
  const [status, setStatus] = useState("loading");
  const [selected, setSelected] = useState(null);
  const [tab, setTab] = useState("overview");

  useEffect(() => {
    loadResults()
      .then((js) => {
        setJobs(js);
        setStatus(js.length ? "ready" : "empty");
      })
      .catch(() => setStatus("error"));
  }, []);

  const { models, scenarios, cell, rewardDims } = useMemo(() => {
    const present = new Set(jobs.map((j) => j._model));
    const models = [
      ...MODEL_ORDER.filter((m) => present.has(m)),
      ...[...present].filter((m) => !MODEL_ORDER.includes(m)),
    ];
    const scenarios = [...new Set(jobs.map((j) => j._scenario))].sort();
    const cell = {};
    for (const j of jobs) cell[`${j._scenario}|${j._model}`] = j;
    // Reward dimensions actually present in the results: the quality scores
    // (every key in `scores` except the `composite` aggregate) plus cost as its
    // own axis. Derived from the data so the chip can't drift from reality.
    const sampleScores = jobs.find((j) => j.scores)?.scores ?? {};
    const qualityDims = Object.keys(sampleScores).filter((k) => k !== "composite").length;
    const hasCost = jobs.some((j) => j.cost?.cost_usd != null);
    const rewardDims = qualityDims + (hasCost ? 1 : 0);
    return { models, scenarios, cell, rewardDims };
  }, [jobs]);

  const ready = status === "ready";

  return (
    <>
      <header className="hero">
        <div className="container hero-inner">
          <div>
            <div className="hero-title">
              <span className="hero-logo">🔥</span>
              <h1>Fire<span>Drill</span></h1>
            </div>
            <p>
              An agent gym for incident response. Each model is dropped into a broken
              software project and scored on whether it fixed the incident, how precisely
              (blast radius), how well it diagnosed it, and what it cost.
            </p>
          </div>
          {ready && (
            <div className="chips">
              <span className="chip"><strong>{scenarios.length}</strong> scenarios</span>
              <span className="chip"><strong>{models.length}</strong> models</span>
              <span className="chip"><strong>{rewardDims}</strong> reward dims</span>
              <span className="chip"><strong>{jobs.length}</strong> jobs</span>
            </div>
          )}
        </div>
      </header>

      <div className="container">
        {ready && (
          <nav className="tabs-bar">
            <button className={`tab-btn ${tab === "overview" ? "active" : ""}`} onClick={() => setTab("overview")}>
              Overview
            </button>
            {models.map((m) => (
              <button key={m} className={`tab-btn ${tab === m ? "active" : ""}`} onClick={() => setTab(m)}>
                {modelLabel(m)}
              </button>
            ))}
          </nav>
        )}

        {status === "loading" && <p className="notice">Loading results…</p>}
        {status === "error" && (
          <p className="notice">
            Couldn’t load <code>{RESULTS_BASE}manifest.json</code>. Run the matrix first
            (<code>orchestrator/run_matrix.sh</code>), or check S3/CORS.
          </p>
        )}
        {status === "empty" && <p className="notice">No results yet — the manifest is empty.</p>}

        {ready && (
          <div className="tab-panel">
            {tab === "overview" ? (
              <Overview
                jobs={jobs}
                models={models}
                scenarios={scenarios}
                cell={cell}
                onSelect={setSelected}
                onPickModel={setTab}
              />
            ) : (
              <ModelTab model={tab} jobs={jobs} allModels={models} onSelect={setSelected} />
            )}
          </div>
        )}

        <footer>
          Results read live from S3 ·{" "}
          <a href="https://github.com/Rhomboic/FireDrill">github.com/Rhomboic/FireDrill</a>
        </footer>
      </div>

      {selected && <Drawer job={selected} onClose={() => setSelected(null)} />}
    </>
  );
}
