import React, { useEffect, useState } from "react";
import logo from "../assets/firedrill_logo.png";

// First-load overlay: show the title + spinner, cross-fade the title into the
// logo after a beat, then reveal the page once BOTH the animation has played and
// the data has loaded (whichever finishes last).
export default function Splash({ dataReady }) {
  const [stage, setStage] = useState("title"); // "title" -> "icon"
  const [minDone, setMinDone] = useState(false);
  const [hidden, setHidden] = useState(false);
  const [gone, setGone] = useState(false);

  useEffect(() => {
    const toIcon = setTimeout(() => setStage("icon"), 500);
    const minHold = setTimeout(() => setMinDone(true), 1000);
    return () => {
      clearTimeout(toIcon);
      clearTimeout(minHold);
    };
  }, []);

  useEffect(() => {
    if (dataReady && minDone && !hidden) {
      setHidden(true);
      const t = setTimeout(() => setGone(true), 500); // match the opacity transition
      return () => clearTimeout(t);
    }
  }, [dataReady, minDone, hidden]);

  if (gone) return null;

  return (
    <div className={`splash${hidden ? " hidden" : ""}`}>
      <div className="splash-card">
        <div className={`splash-stage${stage === "icon" ? " to-icon" : ""}`}>
          <div className="splash-title">
            <h1>Fire<span>Drill</span></h1>
            <p>Incident-response agent gym</p>
          </div>
          <img className="splash-icon" src={logo} alt="FireDrill" />
        </div>
        <div className="splash-spinner" />
      </div>
    </div>
  );
}
