import { Component, lazy, Suspense, useState } from "react";
import { ATTRIBUTION } from "open-anatomy-3d";
import { bodyCallouts, ValueLabel } from "./anatomyData";

const Anatomy3DViewer = lazy(() => import("./Anatomy3DViewer"));
const diagramImage = "/assets/2D-model-transparent.webp";

class ViewerErrorBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <div className="viewer-error"><strong>3D model unavailable</strong><span>Switch to 2D or check this browser’s WebGL support.</span><button type="button" onClick={this.props.onFallback}>Show 2D view</button></div>;
    return this.props.children;
  }
}

export default function AnatomyPanel({ metrics, caseId }) {
  const [view, setView] = useState("2d");
  const visibleCallouts = bodyCallouts.filter((item) => item.key === "Solar8000/NIBP_SBP"
    ? metrics[item.key] || metrics["Solar8000/NIBP_DBP"]
    : metrics[item.key]);
  return <section className="panel body-panel" aria-label="Body overview with available measurements">
    <div className="panel-heading body-heading">
      <div><p className="eyebrow">{caseId ? `Case ${caseId} overview` : "Patient overview"}</p><h2>Signals at a glance</h2></div>
      <div className="anatomy-tools">
        <span className="illustration-note">{view === "3d" ? "Drag to rotate · pinch to zoom" : "Illustrative body map"}</span>
        <div className="view-toggle" role="group" aria-label="Anatomy view">
          <button type="button" aria-pressed={view === "2d"} onClick={() => setView("2d")}>2D</button>
          <button type="button" aria-pressed={view === "3d"} onClick={() => setView("3d")}>3D</button>
        </div>
      </div>
    </div>
    <div className={`anatomy-stage anatomy-stage-${view}`}>
      {view === "2d" ? <>
        <img className="anatomy-2d-image" src={diagramImage} alt="Illustrative full-body anatomical diagram showing major organ systems" />
        <svg className="anatomy-lines" viewBox="0 0 1000 700" preserveAspectRatio="none" aria-hidden="true">
          {visibleCallouts.map((item) => {
            const [x, y] = item.anchor2d;
            const startX = item.side === "left" ? 205 : 795;
            const elbowX = item.side === "left" ? 390 : 610;
            return <g key={item.key}><polyline points={`${startX},${item.labelY} ${elbowX},${item.labelY} ${x},${y}`} /><circle cx={x} cy={y} r="5" /></g>;
          })}
        </svg>
        <div className="body-labels body-labels-left">{visibleCallouts.filter((item) => item.side === "left").map((item) => <ValueLabel key={item.key} item={item} metrics={metrics} style={{ top: `${item.labelY / 700 * 100}%` }} />)}</div>
        <div className="body-labels body-labels-right">{visibleCallouts.filter((item) => item.side === "right").map((item) => <ValueLabel key={item.key} item={item} metrics={metrics} style={{ top: `${item.labelY / 700 * 100}%` }} />)}</div>
      </> : <ViewerErrorBoundary key="3d" onFallback={() => setView("2d")}>
        <Suspense fallback={<div className="viewer-loading">Loading interactive 3D model…</div>}>
          <Anatomy3DViewer metrics={metrics} />
        </Suspense>
      </ViewerErrorBoundary>}
    </div>
  </section>;
}
