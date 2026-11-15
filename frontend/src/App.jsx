import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AnatomyPanel from "./AnatomyPanel";
import SpaceBackground from "./SpaceBackground";
import EnvironmentalPanel from "./EnvironmentalPanel";

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const metricLabels = {
  "Solar8000/HR": "Heart rate",
  "Solar8000/NIBP_SBP": "Systolic BP",
  "Solar8000/NIBP_DBP": "Diastolic BP",
  "Solar8000/PLETH_SPO2": "Oxygen saturation",
  "Solar8000/BT": "Body temperature",
  "Solar8000/RR": "Respiratory rate",
};
const metricShort = {
  "Solar8000/HR": "Heart rate", "Solar8000/NIBP_SBP": "Systolic BP",
  "Solar8000/NIBP_DBP": "Diastolic BP", "Solar8000/PLETH_SPO2": "SpO₂",
  "Solar8000/BT": "Temperature", "Solar8000/RR": "Respiratory rate",
};
const replayTracks = Object.keys(metricLabels);
const scenarios = ["normal", "tachycardia", "hypoxia", "hypotension"];
const demoSeeds = {
  "Solar8000/HR": [72, "bpm"], "Solar8000/NIBP_SBP": [118, "mmHg"],
  "Solar8000/NIBP_DBP": [76, "mmHg"], "Solar8000/PLETH_SPO2": [98, "%"],
  "Solar8000/BT": [36.6, "°C"], "Solar8000/RR": [16, "/min"],
};

function seededNoise(seconds, phase) {
  const value = Math.sin((seconds + phase) * 12.9898) * 43758.5453;
  return (value - Math.floor(value)) * 2 - 1;
}

function demoSignalValue(metric, baseline, seconds) {
  const phases = { "Solar8000/HR": 0, "Solar8000/NIBP_SBP": 3, "Solar8000/NIBP_DBP": 6, "Solar8000/PLETH_SPO2": 9, "Solar8000/BT": 2, "Solar8000/RR": 5 };
  const phase = phases[metric] || 0;
  const breathing = Math.sin((seconds / 5.5) * Math.PI * 2 + phase) * (metric === "Solar8000/HR" ? 1.5 : 0.25);
  const slowDrift = Math.sin(seconds / 31 + phase) * (metric === "Solar8000/HR" ? 1.2 : 0.35)
    + Math.sin(seconds / 79 + phase) * (metric === "Solar8000/HR" ? 0.8 : 0.2);
  const correlatedNoise = seededNoise(seconds - 1, phase) * 0.65 + seededNoise(seconds, phase) * 0.35;
  const noiseScale = metric === "Solar8000/HR" ? 0.9
    : metric.includes("NIBP_") ? 1.2
      : metric === "Solar8000/RR" ? 0.45
        : metric === "Solar8000/BT" ? 0.04 : 0.12;
  const value = Number(baseline) + breathing + slowDrift + correlatedNoise * noiseScale;
  return metric === "Solar8000/HR" || metric.includes("NIBP_") || metric === "Solar8000/RR"
    ? Math.max(0, Math.round(value))
    : Number(value.toFixed(1));
}

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" }, ...options,
  });
  if (!response.ok) throw new Error((await response.text()) || `Request failed (${response.status})`);
  return response.json();
}

function metricName(metric) { return metricLabels[metric] || metric.replaceAll("/", " / "); }
function displayValue(value, unit) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  const number = Number(value);
  return `${Number.isInteger(number) ? number : number.toFixed(1)}${unit ? ` ${unit}` : ""}`;
}
function SignalCoverage({ latestByMetric, simulated }) {
  const trackedSignals = [
    ["Heart rate", "Solar8000/HR"],
    ["Systolic BP", "Solar8000/NIBP_SBP"],
    ["Diastolic BP", "Solar8000/NIBP_DBP"],
    ["SpO₂", "Solar8000/PLETH_SPO2"],
    ["Temperature", "Solar8000/BT"],
    ["Respiratory rate", "Solar8000/RR"],
  ];
  const available = trackedSignals.filter(([, key]) => latestByMetric[key]).length;
  const coverage = Math.round(available / trackedSignals.length * 100);
  return <article className="panel heart-score-panel">
    <div className="panel-heading"><div><p className="eyebrow">{simulated ? "Local stream" : "Telemetry availability"}</p><h2>{simulated ? "Simulated signals" : "Signal coverage"}</h2></div><span className="score-live-dot" aria-label={simulated ? "Demo stream active" : "Coverage indicator"} /></div>
    <div className="heart-score-content">
      <div className="score-gauge" style={{ "--score": `${coverage}%` }}><div className="score-gauge-inner"><span>{simulated ? "1 Hz" : `${available}/${trackedSignals.length}`}</span><small>{simulated ? "Demo update" : "Signals available"}</small></div></div>
      <div className="score-breakdown">{trackedSignals.map(([label, key]) => <div className="score-row" key={key}><span className="score-row-icon" aria-hidden="true">{latestByMetric[key] ? "●" : "○"}</span><span className="score-row-label">{label}<small>{latestByMetric[key] ? displayValue(latestByMetric[key].value, latestByMetric[key].unit) : "No reading"}</small></span><strong className={`score-rating ${latestByMetric[key] ? "score-good" : "score-waiting"}`}>{simulated ? "Demo" : latestByMetric[key] ? "Available" : "Missing"}</strong></div>)}</div>
    </div>
    <p className="score-disclaimer">{simulated ? "Synthetic values for interface demonstration; not sensor telemetry." : "Coverage of configured signals only. Not a crew health or readiness score."}</p>
  </article>;
}
function timeLabel(value, options = {}) {
  if (!value) return "—";
  return new Date(value).toLocaleString([], { hour: "2-digit", minute: "2-digit", ...options });
}
function StatusBadge({ status, simulated = false }) {
  const label = simulated ? "Stored data only" : status === "attention" ? "Review flagged window" : status === "monitoring" ? "No anomaly flagged" : (status || "Unknown").replaceAll("_", " ");
  return <span className={`status-badge status-${status}`}>{label}</span>;
}

function TrendChart({ points, metric = "Solar8000/HR", onPointSelect, selectedIndex = null, anomalies = [] }) {
  const width = 720, height = 210, pad = { left: 40, right: 12, top: 16, bottom: 30 };
  const [hoverIndex, setHoverIndex] = useState(null);
  if (!points.length) return <div className="chart-empty">{metricName(metric)} history will appear when timestamped readings are available.</div>;
  const values = points.map((point) => Number(point.value));
  const low = Math.min(...values), high = Math.max(...values);
  const spread = high - low || Math.max(Math.abs(high) * 0.08, 1);
  const min = low - spread * 0.15, max = high + spread * 0.15;
  const x = (index) => pad.left + (points.length < 2 ? 0 : index * (width - pad.left - pad.right) / (points.length - 1));
  const y = (value) => pad.top + (max - Number(value)) * (height - pad.top - pad.bottom) / (max - min);
  const line = points.map((point, index) => `${x(index)},${y(point.value)}`).join(" ");
  const area = `${pad.left},${height - pad.bottom} ${line} ${x(points.length - 1)},${height - pad.bottom}`;
  const ticks = [0, Math.floor((points.length - 1) / 2), points.length - 1].filter((tick, index, all) => all.indexOf(tick) === index);
  const pointFromEvent = (event) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const chartX = (event.clientX - bounds.left) * width / bounds.width;
    const ratio = Math.max(0, Math.min(1, (chartX - pad.left) / (width - pad.left - pad.right)));
    return Math.round(ratio * (points.length - 1));
  };
  const activeIndex = hoverIndex ?? selectedIndex;
  const activePoint = activeIndex === null ? null : points[activeIndex];
  const tooltipX = activeIndex === null ? 0 : Math.max(94, Math.min(width - 94, x(activeIndex)));
  const tooltipY = activeIndex === null ? 0 : Math.max(39, y(activePoint.value) - 35);
  const pointTime = (value) => new Date(value).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const flags = anomalies.flatMap((anomaly) => {
    const startTime = new Date(anomaly.window_start).getTime();
    const endTime = new Date(anomaly.window_end).getTime();
    const start = points.findIndex((point) => new Date(point.recorded_at).getTime() >= startTime);
    let end = points.findIndex((point) => new Date(point.recorded_at).getTime() >= endTime);
    if (start < 0 || new Date(points[start].recorded_at).getTime() > endTime) return [];
    if (end < 0) end = points.length - 1;
    return [{ start, end: Math.max(start, end) }];
  });
  return <div className="chart-wrap"><svg className="trend-chart" viewBox={`0 0 ${width} ${height}`} role="application" tabIndex="0" aria-label={`${metricName(metric)} trend from ${points.length} recorded measurements. Use arrow keys to inspect points.`}
    onPointerMove={(event) => setHoverIndex(pointFromEvent(event))} onPointerLeave={() => setHoverIndex(null)}
    onClick={(event) => onPointSelect?.(pointFromEvent(event))}
    onKeyDown={(event) => { if (!["ArrowLeft", "ArrowRight", "Home", "End", "Enter"].includes(event.key)) return; event.preventDefault(); const current = selectedIndex ?? points.length - 1; const next = event.key === "ArrowLeft" ? Math.max(0, current - 1) : event.key === "ArrowRight" ? Math.min(points.length - 1, current + 1) : event.key === "Home" ? 0 : event.key === "End" ? points.length - 1 : current; onPointSelect?.(next); }}>
    <defs><linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#ff7189" stopOpacity=".34"/><stop offset="1" stopColor="#ff7189" stopOpacity="0"/></linearGradient></defs>
    {[0, 1, 2].map((tick) => { const yy = pad.top + tick * (height - pad.top - pad.bottom) / 2; const val = max - tick * (max - min) / 2; return <g key={tick}><line x1={pad.left} x2={width - pad.right} y1={yy} y2={yy} className="chart-gridline"/><text x={pad.left - 9} y={yy + 4} textAnchor="end" className="chart-axis">{val.toFixed(0)}</text></g>; })}
    {flags.map((flag, index) => <rect key={index} x={x(flag.start)} y={pad.top} width={Math.max(3, x(flag.end) - x(flag.start))} height={height - pad.top - pad.bottom} className="chart-flag-window" rx="3" />)}
    <polygon points={area} fill="url(#trendFill)"/><polyline points={line} className="chart-line"/>
    {activeIndex !== null && <g className="chart-active-point"><line x1={x(activeIndex)} x2={x(activeIndex)} y1={pad.top} y2={height - pad.bottom} /><circle cx={x(activeIndex)} cy={y(activePoint.value)} r="5" /><g transform={`translate(${tooltipX},${tooltipY})`}><rect x="-87" y="-25" width="174" height="46" rx="7"/><text y="-7" textAnchor="middle">{displayValue(activePoint.value, activePoint.unit)}</text><text y="9" textAnchor="middle" className="chart-tooltip-time">{pointTime(activePoint.recorded_at)}</text></g></g>}
    {ticks.map((tick) => <text key={tick} x={x(tick)} y={height - 7} textAnchor={tick === 0 ? "start" : tick === points.length - 1 ? "end" : "middle"} className="chart-axis">{timeLabel(points[tick].recorded_at)}</text>)}
  </svg></div>;
}

function App() {
  const [health, setHealth] = useState(null), [cases, setCases] = useState([]), [selectedCase, setSelectedCase] = useState("");
  const [scenario, setScenario] = useState("normal"), [summary, setSummary] = useState(null), [measurements, setMeasurements] = useState([]);
  const [pollSeconds, setPollSeconds] = useState(5);
  const [displayMode, setDisplayMode] = useState("simulation"), [simulationRunning, setSimulationRunning] = useState(true);
  const [simulationNow, setSimulationNow] = useState(() => Date.now());
  const [trendMetric, setTrendMetric] = useState("Solar8000/HR"), [trendRange, setTrendRange] = useState("all");
  const [reviewIndex, setReviewIndex] = useState(null), [reviewPlaying, setReviewPlaying] = useState(false), [reviewSpeed, setReviewSpeed] = useState(1);
  const [pendingAnomaly, setPendingAnomaly] = useState(null);
  const [question, setQuestion] = useState(""), [answer, setAnswer] = useState(""), [loading, setLoading] = useState(true);
  const [replayLoading, setReplayLoading] = useState(false), [assistantLoading, setAssistantLoading] = useState(false);
  const [error, setError] = useState(""), [replayMessage, setReplayMessage] = useState(""), [liveReplay, setLiveReplay] = useState(true);
  const replayBusy = useRef(false), initialReplayStarted = useRef(false);
  const caseQuery = selectedCase ? `?case_id=${encodeURIComponent(selectedCase)}` : "";

  const loadDashboard = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const [healthData, caseData, summaryData, measurementData] = await Promise.all([
        request("/health"), request("/cases"), request(`/health-summary${caseQuery}`),
        request(`/measurements${selectedCase ? `${caseQuery}&` : "?"}limit=100`),
      ]);
      setHealth(healthData); setCases(caseData); setSummary(summaryData); setMeasurements(measurementData);
    } catch (requestError) { setError(requestError.message); }
    finally { setLoading(false); }
  }, [caseQuery, selectedCase]);
  useEffect(() => { loadDashboard(); }, [loadDashboard]);

  const ingestReplay = useCallback(async () => {
    if (replayBusy.current) return;
    replayBusy.current = true; setReplayLoading(true); setError(""); setReplayMessage("");
    try {
      const latestTimestamp = measurements.reduce((latest, row) => !latest || row.recorded_at > latest ? row.recorded_at : latest, null);
      const at = latestTimestamp ? new Date(new Date(latestTimestamp).getTime() + 10_000).toISOString() : null;
      const results = await Promise.allSettled(replayTracks.map((track_code) => request("/ingest/vitaldb/replay", {
        method: "POST", body: JSON.stringify({ location: "OR1", track_code, window_seconds: 10, scenario, ...(at ? { at } : {}) }),
      })));
      const successful = results.filter((result) => result.status === "fulfilled"), failed = results.length - successful.length;
      if (!successful.length) throw new Error("VitalDB replay could not provide any requested physiological tracks.");
      const received = successful.reduce((total, result) => total + result.value.received, 0);
      setReplayMessage(`${received} samples received across ${successful.length} of ${replayTracks.length} tracks${failed ? `; ${failed} unavailable` : ""}. Scenario: ${scenario}.`);
      await loadDashboard();
    } catch (requestError) { setError(requestError.message); }
    finally { setReplayLoading(false); replayBusy.current = false; }
  }, [loadDashboard, measurements, scenario]);
  useEffect(() => {
    if (!loading && displayMode === "recorded" && liveReplay && !initialReplayStarted.current) { initialReplayStarted.current = true; void ingestReplay(); }
  }, [displayMode, ingestReplay, liveReplay, loading]);
  useEffect(() => {
    if (displayMode !== "recorded" || !liveReplay) return undefined;
    const interval = window.setInterval(() => void ingestReplay(), pollSeconds * 1000);
    return () => window.clearInterval(interval);
  }, [displayMode, ingestReplay, liveReplay, pollSeconds]);
  useEffect(() => {
    if (displayMode !== "simulation" || !simulationRunning) return undefined;
    const timer = window.setInterval(() => setSimulationNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [displayMode, simulationRunning]);

  const latestMeasurements = useMemo(() => [...(summary?.latest_measurements?.length ? summary.latest_measurements : measurements)].sort((a, b) => new Date(b.recorded_at) - new Date(a.recorded_at)), [measurements, summary]);
  const focusedCase = selectedCase || latestMeasurements[0]?.case_id || "";
  const caseMeasurements = useMemo(() => latestMeasurements.filter((row) => row.case_id === focusedCase), [focusedCase, latestMeasurements]);
  const latestByMetric = useMemo(() => {
    const latest = caseMeasurements.reduce((result, row) => {
      if (!result[row.metric]) result[row.metric] = row;
      return result;
    }, {});
    if (latest["Solar8000/NIBP_SBP"]) latest["Solar8000/NIBP_SBP"].companion = latest["Solar8000/NIBP_DBP"];
    else if (latest["Solar8000/NIBP_DBP"]) latest["Solar8000/NIBP_DBP"].companion = null;
    return latest;
  }, [caseMeasurements]);
  const simulatedMeasurements = useMemo(() => {
    const currentSeconds = Math.floor(simulationNow / 1000);
    return replayTracks.flatMap((metric) => {
      const [seedValue, seedUnit] = demoSeeds[metric];
      const baselineRow = latestByMetric[metric];
      const baseline = baselineRow && Number.isFinite(Number(baselineRow.value)) ? Number(baselineRow.value) : seedValue;
      const unit = baselineRow?.unit || seedUnit;
      return Array.from({ length: 60 }, (_, index) => {
        const secondsAgo = 59 - index;
        return { case_id: "LOCAL-DEMO", metric, value: demoSignalValue(metric, baseline, currentSeconds - secondsAgo), unit, recorded_at: new Date(simulationNow - secondsAgo * 1000).toISOString(), source: "Local 1-second demo simulation" };
      });
    });
  }, [latestByMetric, simulationNow]);
  const uiMeasurements = displayMode === "simulation" ? simulatedMeasurements : measurements;
  const uiLatestByMetric = useMemo(() => displayMode === "simulation"
    ? Object.fromEntries(replayTracks.map((metric) => [metric, simulatedMeasurements.findLast((row) => row.metric === metric)]))
    : latestByMetric, [displayMode, latestByMetric, simulatedMeasurements]);
  const uiCaseMeasurements = displayMode === "simulation"
    ? replayTracks.map((metric) => uiLatestByMetric[metric]).filter(Boolean)
    : caseMeasurements;
  const uiFocusedCase = displayMode === "simulation" ? "LOCAL-DEMO" : focusedCase;
  const uiLatestMeasurements = displayMode === "simulation" ? uiCaseMeasurements : latestMeasurements;
  const heartRatePoints = useMemo(() => uiMeasurements.filter((row) => row.metric === "Solar8000/HR" && (displayMode === "simulation" || !focusedCase || row.case_id === focusedCase)).sort((a, b) => new Date(a.recorded_at) - new Date(b.recorded_at)), [displayMode, focusedCase, uiMeasurements]);
  const metricPoints = useMemo(() => uiMeasurements.filter((row) => row.metric === trendMetric && (displayMode === "simulation" || !focusedCase || row.case_id === focusedCase)).sort((a, b) => new Date(a.recorded_at) - new Date(b.recorded_at)), [displayMode, focusedCase, uiMeasurements, trendMetric]);
  const rangePoints = useMemo(() => {
    if (trendRange === "all" || !metricPoints.length) return metricPoints;
    const duration = Number(trendRange) * 60_000;
    const cutoff = new Date(metricPoints.at(-1).recorded_at).getTime() - duration;
    return metricPoints.filter((row) => new Date(row.recorded_at).getTime() >= cutoff);
  }, [metricPoints, trendRange]);
  const trendPoints = reviewIndex === null ? rangePoints : rangePoints.slice(0, Math.min(reviewIndex + 1, rangePoints.length));
  useEffect(() => {
    if (!reviewPlaying) return undefined;
    if (reviewIndex !== null && reviewIndex >= rangePoints.length - 1) { setReviewPlaying(false); return undefined; }
    const timer = window.setInterval(() => setReviewIndex((index) => Math.min((index ?? 0) + 1, rangePoints.length - 1)), 1000 / reviewSpeed);
    return () => window.clearInterval(timer);
  }, [rangePoints.length, reviewIndex, reviewPlaying, reviewSpeed]);
  useEffect(() => {
    if (!pendingAnomaly || loading || !measurements.some((row) => row.case_id === pendingAnomaly.caseId)) return;
    const timestamp = new Date(pendingAnomaly.windowStart).getTime();
    let closestIndex = 0, closestDistance = Infinity;
    metricPoints.forEach((point, index) => {
      const distance = Math.abs(new Date(point.recorded_at).getTime() - timestamp);
      if (distance < closestDistance) { closestDistance = distance; closestIndex = index; }
    });
    if (metricPoints.length) { setReviewIndex(closestIndex); setReviewPlaying(false); document.getElementById("signal-trend")?.scrollIntoView({ behavior: "smooth", block: "center" }); }
    setPendingAnomaly(null);
  }, [loading, measurements, metricPoints, pendingAnomaly]);

  function focusAnomaly(anomaly) {
    const caseId = String(anomaly.case_id || "");
    setDisplayMode("recorded"); setSimulationRunning(false);
    setTrendMetric("Solar8000/HR"); setTrendRange("all"); setReviewIndex(null); setReviewPlaying(false);
    setPendingAnomaly({ caseId, windowStart: anomaly.window_start });
    if (caseId) setSelectedCase(caseId);
  }
  function selectMetric(metric) {
    if (!replayTracks.includes(metric)) return;
    setTrendMetric(metric); setReviewIndex(null); setReviewPlaying(false);
    document.getElementById("signal-trend")?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  async function askAssistant(event) {
    event.preventDefault(); if (!question.trim() || displayMode === "simulation") return;
    setAssistantLoading(true); setError("");
    try { const result = await request(`/assistant/explain${caseQuery}`, { method: "POST", body: JSON.stringify({ question: question.trim() }) }); setAnswer(result.answer); }
    catch (requestError) { setError(requestError.message); }
    finally { setAssistantLoading(false); }
  }

  function openAssistant() {
    setDisplayMode("recorded");
    setSimulationRunning(false);
    setAnswer("");
    setError("");
  }

  return <div className="app-shell">
    <SpaceBackground />
    <header className="topbar"><a className="brand" href="#top" aria-label="Health Gizmo crew monitoring dashboard"><span className="brand-mark">HG</span><span><small>Crew monitoring platform</small><strong>Health Gizmo</strong></span></a>
      <div className="header-center"><span className={`live-indicator ${displayMode === "simulation" ? simulationRunning ? "is-live" : "" : liveReplay ? "is-live" : ""}`}><i />{displayMode === "simulation" ? simulationRunning ? "1-sec demo stream" : "Demo paused" : liveReplay ? "Recorded replay polling" : "Replay paused"}</span><span className="header-divider"/><span className="source-label">{displayMode === "simulation" ? "SIMULATED VALUES · NOT TELEMETRY" : `${health?.data_source || "VitalDB"} replay · not crew telemetry`}</span></div>
      <div className="topbar-actions"><button className="icon-button" title="Refresh source data" aria-label="Refresh source data" onClick={loadDashboard}>↻</button><button className="quiet-button" disabled={replayLoading} onClick={ingestReplay}>{replayLoading ? "Collecting…" : "Ingest window"}</button><button className="quiet-button pause-button" onClick={() => displayMode === "simulation" ? setSimulationRunning((active) => !active) : setLiveReplay((active) => !active)}>{displayMode === "simulation" ? simulationRunning ? "Pause demo" : "Resume demo" : liveReplay ? "Pause replay" : "Resume replay"}</button></div>
    </header>
    <main id="top" className="dashboard">
      <section className="intro-row"><div><p className="eyebrow">{displayMode === "simulation" ? "Crew monitoring interface · local demo" : "Crew health monitoring · replay environment"}</p><h1>Mission signals overview</h1><p className="intro-copy">{displayMode === "simulation" ? "Synthetic values update every second from the selected case baseline and are never saved as measurements." : "Recorded physiological data for interface demonstration. No live crew link is connected."}</p></div><div className="filters">
        <label><span>Display mode</span><select value={displayMode} onChange={(event) => { setDisplayMode(event.target.value); setSimulationRunning(true); setReviewIndex(null); setReviewPlaying(false); setTrendRange("all"); setAnswer(""); }}><option value="simulation">1-sec demo stream</option><option value="recorded">Recorded data</option></select></label>
        <label><span>Replay case</span><select value={selectedCase} onChange={(event) => setSelectedCase(event.target.value)}><option value="">All cases</option>{cases.map((caseId) => <option key={caseId} value={caseId}>Case {caseId}</option>)}</select></label>
        <label><span>Replay scenario</span><select value={scenario} onChange={(event) => setScenario(event.target.value)}>{scenarios.map((value) => <option key={value} value={value}>{value === "normal" ? "Recorded values" : `Demo transform: ${value}`}</option>)}</select></label>
        {displayMode === "recorded" && <label><span>Replay cadence</span><select value={pollSeconds} onChange={(event) => setPollSeconds(Number(event.target.value))}><option value="5">Every 5 seconds</option><option value="10">Every 10 seconds</option></select></label>}
      </div></section>
      {error && <div className="notice error-notice" role="alert">{error}</div>}{replayMessage && <div className="notice success-notice" role="status">{replayMessage}</div>}

      <section className="overview-grid">
        <aside className="left-column">
          <article className="panel pulse-panel"><div className="panel-heading"><div><p className="eyebrow">{displayMode === "simulation" ? "Simulated · 1 Hz" : "Latest reading"}</p><h2>Heart rate</h2></div><span className="metric-symbol pulse-symbol">⌁</span></div><strong className="big-reading">{displayValue(uiLatestByMetric["Solar8000/HR"]?.value, uiLatestByMetric["Solar8000/HR"]?.unit)}</strong><span className="reading-time">{uiLatestByMetric["Solar8000/HR"] ? `${displayMode === "simulation" ? "Demo tick" : "Recorded"} ${timeLabel(uiLatestByMetric["Solar8000/HR"].recorded_at, { month: "short", day: "numeric", second: "2-digit" })}` : "Awaiting measurement"}</span><div className="sparkline"><TrendChart points={heartRatePoints.slice(-28)} /></div></article>
          <article className="panel vitals-panel"><div className="panel-heading"><div><p className="eyebrow">Latest by signal</p><h2>{displayMode === "simulation" ? "Values" : "Health metrics"}</h2></div><span className="subtle-count">{Object.keys(uiLatestByMetric).length} available</span></div>
            {uiCaseMeasurements.length ? <div className="vitals-list">{uiCaseMeasurements.map((row) => <button type="button" className={`vital-row ${trendMetric === row.metric ? "active" : ""}`} key={`${row.case_id}-${row.metric}`} onClick={() => selectMetric(row.metric)} aria-label={`Show ${metricName(row.metric)} trend`}><span className="vital-icon">{row.metric === "Solar8000/HR" ? "⌁" : row.metric === "Solar8000/PLETH_SPO2" ? "◌" : row.metric.includes("NIBP") ? "＋" : row.metric === "Solar8000/BT" ? "°" : "≋"}</span><span className="vital-name">{metricShort[row.metric] || metricName(row.metric)}</span><strong>{displayValue(row.value, row.unit)}</strong></button>)}</div> : <EmptyState title="No readings yet" copy="Recorded measurements will appear here." compact />}
          </article>
          <SignalCoverage latestByMetric={uiLatestByMetric} simulated={displayMode === "simulation"} />
        </aside>
        <AnatomyPanel metrics={uiLatestByMetric} caseId={uiFocusedCase} onMetricSelect={selectMetric} />
        <aside className="right-column">
          <article className="panel status-panel"><div className="panel-heading"><div><p className="eyebrow">Pattern analysis</p><h2>{displayMode === "simulation" ? "Recorded-data model output" : "Anomaly model output"}</h2></div><span className={`status-orb ${summary?.status === "attention" ? "attention" : ""}`} /></div><div className="status-main"><StatusBadge status={health?.model_loaded ? (summary?.status || "insufficient_data") : "model_unavailable"} simulated={displayMode === "simulation"}/><span>{displayMode === "simulation" ? "Not applied to demo stream" : health?.model_loaded ? "Model loaded" : "Model unavailable"}</span></div><div className="status-divider"/><div className="mini-stat-grid"><div><strong>{summary?.anomalies?.length || 0}</strong><span>Flagged stored-data windows</span></div><div><strong>{summary?.trend_windows || 0}</strong><span>Stored-data feature windows</span></div></div>
            <h3 className="section-caption">{displayMode === "simulation" ? "Stored-data anomalies · select to inspect" : "Detected anomalies · select to inspect"}</h3>{summary?.anomalies?.length ? <div className="anomaly-list">{summary.anomalies.slice(0, 3).map((anomaly) => <button type="button" className="anomaly-item anomaly-button" key={`${anomaly.case_id}-${anomaly.window_start}`} onClick={() => focusAnomaly(anomaly)} aria-label={`Inspect flagged window for case ${anomaly.case_id || "unknown"} at ${timeLabel(anomaly.window_start)}`}><span className="anomaly-mark">!</span><span><strong>Review window</strong><small>Case {anomaly.case_id || "unknown"} · {timeLabel(anomaly.window_start, { month: "short", day: "numeric" })}</small></span><b>{Number(anomaly.score).toFixed(2)}</b></button>)}</div> : <p className="quiet-empty">{displayMode === "simulation" ? "No stored-data anomaly windows. The local stream is not scored." : "No active anomaly windows reported."}</p>}
          </article>
          <article className="panel assistant-panel"><div className="panel-heading"><div><p className="eyebrow">Crew data explainer</p><h2>Ask the monitoring assistant</h2></div><span className="agent-badge">AI</span></div>{displayMode === "simulation" ? <div className="assistant-gate"><p className="assistant-disclaimer">The assistant answers questions about stored source measurements. Switch from local simulation to recorded data to continue.</p><button type="button" className="assistant-open-button" onClick={openAssistant}>Use recorded data</button></div> : <><form onSubmit={askAssistant} className="assistant-form"><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="Ask about a reading or flagged window" maxLength={2000}/><button type="submit" disabled={assistantLoading || !question.trim()}>{assistantLoading ? "Thinking…" : "Ask"}</button></form>{answer ? <div className="assistant-answer">{answer}</div> : <p className="assistant-disclaimer">Explains available replay data and model output. Not a medical or mission-readiness decision.</p>}</>}</article>
        </aside>
      </section>

      <section className="lower-grid"><article className="panel trend-panel" id="signal-trend"><div className="panel-heading"><div><p className="eyebrow">{displayMode === "simulation" ? "Synthetic local values · 1 sample per second" : "Recorded measurements"} · select a point to inspect</p><h2>{metricName(trendMetric)} trend</h2></div><span className="chart-meta">{rangePoints.length} readings · {uiLatestByMetric[trendMetric]?.unit || "unit unavailable"}</span></div>
          <div className="trend-controls"><div className="trend-metric-switch" role="group" aria-label="Select chart metric">{replayTracks.map((metric) => <button type="button" key={metric} className={trendMetric === metric ? "selected" : ""} aria-pressed={trendMetric === metric} onClick={() => selectMetric(metric)}>{metricShort[metric]}</button>)}</div><div className="trend-range-switch" role="group" aria-label="Select chart time range">{(displayMode === "simulation" ? [["1", "1m"], ["all", "All"]] : [["1", "1m"], ["5", "5m"], ["15", "15m"], ["all", "All"]]).map(([value, label]) => <button type="button" key={value} className={trendRange === value ? "selected" : ""} aria-pressed={trendRange === value} onClick={() => { setTrendRange(value); setReviewIndex(null); setReviewPlaying(false); }}>{label}</button>)}</div></div>
          <TrendChart points={trendPoints} metric={trendMetric} selectedIndex={reviewIndex === null ? null : trendPoints.length - 1} anomalies={displayMode === "recorded" ? summary?.anomalies?.filter((anomaly) => !focusedCase || String(anomaly.case_id) === String(focusedCase)) || [] : []} onPointSelect={(index) => { setReviewIndex(index); setReviewPlaying(false); }} />
          {displayMode === "recorded" ? <div className="replay-controls"><button type="button" className="replay-play-button" disabled={!rangePoints.length} onClick={() => { if (reviewPlaying) setReviewPlaying(false); else { if (reviewIndex === null || reviewIndex >= rangePoints.length - 1) setReviewIndex(0); setReviewPlaying(true); } }}>{reviewPlaying ? "Pause review" : "Play review"}</button><label className="replay-slider-label">Review position<input type="range" min="0" max={Math.max(0, rangePoints.length - 1)} value={reviewIndex === null ? Math.max(0, rangePoints.length - 1) : Math.min(reviewIndex, Math.max(0, rangePoints.length - 1))} disabled={!rangePoints.length} onChange={(event) => { setReviewIndex(Number(event.target.value)); setReviewPlaying(false); }} /></label><label className="replay-speed-label">Speed<select value={reviewSpeed} onChange={(event) => setReviewSpeed(Number(event.target.value))}><option value="0.5">0.5×</option><option value="1">1×</option><option value="2">2×</option><option value="4">4×</option></select></label><span className="replay-position-time">{trendPoints.length ? timeLabel(trendPoints.at(-1).recorded_at, { month: "short", day: "numeric", second: "2-digit" }) : "No points"}</span><button type="button" className="replay-live-button" onClick={() => { setReviewIndex(null); setReviewPlaying(false); }}>Latest</button></div> : <div className={`demo-tick-status ${simulationRunning ? "running" : ""}`}><span />{simulationRunning ? "alues refresh every second" : "Local demo stream paused"}</div>}
          <p className="chart-footnote">{displayMode === "simulation" ? "Values are generated locally from the selected case baseline (or demo seeds); they are not stored or scored." : "Recorded values only; gaps are not interpolated. Review playback browses samples already loaded in this case."}</p></article>
        </section>
      <section className="panel feed-panel"><div className="panel-heading"><div><p className="eyebrow">{displayMode === "simulation" ? "Demo stream · not persisted" : "Signal feed"}</p><h2>{displayMode === "simulation" ? "Current simulated values" : "Latest measurements"}</h2></div>{displayMode === "recorded" && loading && <span className="loading-label">Updating…</span>}</div>{uiLatestMeasurements.length ? <div className="table-wrap"><table><thead><tr><th>Signal</th><th>Value</th><th>Case</th><th>Timestamp</th><th>Source</th></tr></thead><tbody>{uiLatestMeasurements.slice(0, 12).map((row, index) => <tr key={`${row.metric}-${row.recorded_at}-${index}`}><td>{metricName(row.metric)}</td><td className="value-cell">{displayValue(row.value, row.unit)}</td><td>{row.case_id}</td><td>{timeLabel(row.recorded_at, { month: "short", day: "numeric", second: "2-digit" })}</td><td>{row.source || summary?.data_source || "—"}</td></tr>)}</tbody></table></div> : <EmptyState title="No measurements yet" copy="Ingest a VitalDB replay window to populate the monitoring feed."/>}</section>
      <EnvironmentalPanel />
    </main>
    <footer><span>Health Gizmo · crew monitoring prototype</span><span>{displayMode === "simulation" ? "Local synthetic values · never saved · not astronaut telemetry" : `${summary?.data_source || "VitalDB"} replay · not astronaut telemetry · anomaly detection support only`}</span><span>{displayMode === "simulation" ? `Demo ${timeLabel(simulationNow, { month: "short", day: "numeric", second: "2-digit" })}` : summary?.generated_at ? `Summary ${timeLabel(summary.generated_at, { month: "short", day: "numeric" })}` : loading ? "Loading data" : "No summary timestamp"}</span></footer>
  </div>;
}

function EmptyState({ title, copy, compact = false }) { return <div className={`empty-state ${compact ? "compact" : ""}`}><span className="empty-mark">○</span><strong>{title}</strong><span>{copy}</span></div>; }
export default App;
