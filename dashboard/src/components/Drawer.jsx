import React from "react";
import { modelLabel, money } from "../meta.js";

function Diff({ text }) {
  return (
    <pre className="diff">
      {text.split("\n").map((line, i) => {
        let cls = "";
        if (line.startsWith("+") && !line.startsWith("+++")) cls = "add";
        else if (line.startsWith("-") && !line.startsWith("---")) cls = "del";
        return (
          <div key={i} className={cls}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}

export default function Drawer({ job, onClose }) {
  const s = job.scores;
  const cost = job.cost ?? {};
  const diag = job.diagnosis ?? {};
  const verifyOut = job.verification?.success_condition?.output;

  return (
    <div className="drawer">
      <div className="drawer-bg" onClick={onClose} />
      <div className="drawer-panel">
        <button className="close" onClick={onClose} aria-label="Close">
          ×
        </button>
        <h3>{job.scenario}</h3>
        <div className="muted">
          {modelLabel(job._model)} · {job.stack} · {job.difficulty}
        </div>

        <div className="dims">
          <div className="dim">
            <div className="v">{s.composite.toFixed(2)}</div>
            <div className="k">composite</div>
          </div>
          <div className="dim">
            <div className="v">{s.resolution ? "✓" : "✗"}</div>
            <div className="k">resolution</div>
          </div>
          <div className="dim">
            <div className="v">{s.blast_radius.toFixed(2)}</div>
            <div className="k">blast radius</div>
          </div>
          <div className="dim">
            <div className="v">{diag.score}/5</div>
            <div className="k">diagnosis</div>
          </div>
          <div className="dim">
            <div className="v">{money(cost.cost_usd)}</div>
            <div className="k">cost · {job.efficiency?.steps ?? "?"} steps</div>
          </div>
        </div>

        <div className="block">
          <h4>Diagnosis (judge {diag.score}/5)</h4>
          <p>{diag.agent || <em>none submitted</em>}</p>
          {diag.rationale && <p className="muted">{diag.rationale}</p>}
        </div>

        <div className="block">
          <h4>Blast radius</h4>
          <p className="muted">
            modified: {(job.fix?.files_modified ?? []).join(", ") || "none"}
            {job.fix?.unexpected_files?.length ? (
              <>
                {" · "}
                <span className="no">
                  unexpected: {job.fix.unexpected_files.join(", ")}
                </span>
              </>
            ) : null}
            {job.regression_passed != null && (
              <>
                {" · regression "}
                <span className={job.regression_passed ? "ok" : "no"}>
                  {job.regression_passed ? "passed" : "failed"}
                </span>
              </>
            )}
          </p>
        </div>

        {job.fix?.diffs && Object.keys(job.fix.diffs).length > 0 && (
          <div className="block">
            <h4>Fix</h4>
            {Object.entries(job.fix.diffs).map(([path, text]) => (
              <div key={path}>
                <div className="muted">{path}</div>
                <Diff text={text} />
              </div>
            ))}
          </div>
        )}

        <div className="block trace">
          <h4>Transcript ({job.transcript?.length ?? 0} actions)</h4>
          <pre>
            {(job.transcript ?? []).map((t, i) => {
              const hint = t.args?.path || t.args?.command || t.diagnosis || "";
              const status = t.ok === false ? " [err]" : "";
              return (
                <div key={i} className="step">
                  <span className="tool">{t.tool}</span>{" "}
                  {String(hint).slice(0, 80)}
                  {status}
                </div>
              );
            })}
          </pre>
        </div>

        {verifyOut && (
          <div className="block">
            <h4>Objective verification</h4>
            <pre>{verifyOut}</pre>
          </div>
        )}
      </div>
    </div>
  );
}
