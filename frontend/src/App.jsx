import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import AnatomyPanel from "./AnatomyPanel";

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
function signalRating(value, { excellent, good } = {}) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "Waiting";
  if (excellent?.(Number(value))) return "Excellent";
  if (good?.(Number(value))) return "Good";
  return "Review";
}
function HeartScore({ summary, latestByMetric }) {
  const available = summary?.data_quality?.metrics_available?.length || 0;
  const missing = summary?.data_quality?.expected_metrics_missing?.length || 0;
  const expected = available + missing;
  const anomalyPenalty = Math.min(40, (summary?.anomalies?.length || 0) * 20);
  const score = expected
    ? Math.max(0, Math.round((available / expected) * 100 - anomalyPenalty))
    : 0;
  const heartRate = latestByMetric["Solar8000/HR"]?.value;
  const oxygen = latestByMetric["Solar8000/PLETH_SPO2"]?.value;
  const systolic = latestByMetric["Solar8000/NIBP_SBP"]?.value;
  const diastolic = latestByMetric["Solar8000/NIBP_DBP"]?.value;
  const bloodPressure = systolic && diastolic ? `${Math.round(systolic)}/${Math.round(diastolic)}` : "Waiting";
  const rows = [
    ["Rhythm", displayValue(heartRate, "bpm"), signalRating(heartRate, {
      excellent: (value) => value >= 60 && value <= 100,
      good: (value) => value >= 50 && value <= 110,
    })],
    ["Blood pressure", bloodPressure, systolic && diastolic ? "Good" : "Waiting"],
    ["Oxygen level", displayValue(oxygen, "%"), signalRating(oxygen, {
      excellent: (value) => value >= 95,
      good: (value) => value >= 92,
    })],
    ["Data freshness", latestByMetric["Solar8000/HR"] ? "Live" : "Waiting", latestByMetric["Solar8000/HR"] ? "Excellent" : "Waiting"],
  ];
  return <article className="panel heart-score-panel">
    <div className="panel-heading"><div><p className="eyebrow">Signal snapshot</p><h2>Heart health score</h2></div><span className="score-live-dot" aria-label="Live score" /></div>
    <div className="heart-score-content">
      <div className="score-gauge" style={{ "--score": `${score}%` }}><div className="score-gauge-inner"><span>{score}</span><small>Heart Health Score</small></div></div>
      <div className="score-breakdown">{rows.map(([label, value, rating]) => <div className="score-row" key={label}><span className={`score-row-icon score-icon-${label.toLowerCase().replaceAll(" ", "-")}`} aria-hidden="true">{label === "Rhythm" ? "⌁" : label === "Blood pressure" ? "♧" : label === "Oxygen level" ? "◌" : "◷"}</span><span className="score-row-label">{label}<small>{value}</small></span><strong className={`score-rating score-${rating.toLowerCase()}`}>{rating}</strong></div>)}</div>
    </div>
    <p className="score-disclaimer">Derived from monitored signals, not a clinical assessment.</p>
  </article>;
}
function timeLabel(value, options = {}) {
  if (!value) return "—";
  return new Date(value).toLocaleString([], { hour: "2-digit", minute: "2-digit", ...options });
}
function StatusBadge({ status }) {
  const label = status === "attention" ? "Attention" : (status || "Unknown").replaceAll("_", " ");
  return <span className={`status-badge status-${status}`}>{label}</span>;
}

function TrendChart({ points }) {
  const width = 720, height = 210, pad = { left: 40, right: 12, top: 16, bottom: 30 };
  if (!points.length) return <div className="chart-empty">Heart rate history will appear when timestamped readings are available.</div>;
  const values = points.map((point) => Number(point.value));
  const low = Math.min(...values), high = Math.max(...values);
  const spread = high - low || Math.max(Math.abs(high) * 0.08, 1);
  const min = low - spread * 0.15, max = high + spread * 0.15;
  const x = (index) => pad.left + (points.length < 2 ? 0 : index * (width - pad.left - pad.right) / (points.length - 1));
  const y = (value) => pad.top + (max - Number(value)) * (height - pad.top - pad.bottom) / (max - min);
  const line = points.map((point, index) => `${x(index)},${y(point.value)}`).join(" ");
  const area = `${pad.left},${height - pad.bottom} ${line} ${x(points.length - 1)},${height - pad.bottom}`;
  const ticks = [0, Math.floor((points.length - 1) / 2), points.length - 1].filter((tick, index, all) => all.indexOf(tick) === index);
  return <div className="chart-wrap"><svg className="trend-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Heart rate trend from ${points.length} recorded measurements`}>
    <defs><linearGradient id="trendFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#ff7189" stopOpacity=".34"/><stop offset="1" stopColor="#ff7189" stopOpacity="0"/></linearGradient></defs>
    {[0, 1, 2].map((tick) => { const yy = pad.top + tick * (height - pad.top - pad.bottom) / 2; const val = max - tick * (max - min) / 2; return <g key={tick}><line x1={pad.left} x2={width - pad.right} y1={yy} y2={yy} className="chart-gridline"/><text x={pad.left - 9} y={yy + 4} textAnchor="end" className="chart-axis">{val.toFixed(0)}</text></g>; })}
    <polygon points={area} fill="url(#trendFill)"/><polyline points={line} className="chart-line"/>
    {ticks.map((tick) => <text key={tick} x={x(tick)} y={height - 7} textAnchor={tick === 0 ? "start" : tick === points.length - 1 ? "end" : "middle"} className="chart-axis">{timeLabel(points[tick].recorded_at)}</text>)}
  </svg></div>;
}

function App() {
  const [health, setHealth] = useState(null), [cases, setCases] = useState([]), [selectedCase, setSelectedCase] = useState("");
  const [scenario, setScenario] = useState("normal"), [summary, setSummary] = useState(null), [measurements, setMeasurements] = useState([]);
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
    if (!loading && liveReplay && !initialReplayStarted.current) { initialReplayStarted.current = true; void ingestReplay(); }
  }, [ingestReplay, liveReplay, loading]);
  useEffect(() => {
    if (!liveReplay) return undefined;
    const interval = window.setInterval(() => void ingestReplay(), 10_000);
    return () => window.clearInterval(interval);
  }, [ingestReplay, liveReplay]);

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
  const heartRatePoints = useMemo(() => measurements.filter((row) => row.metric === "Solar8000/HR" && (!focusedCase || row.case_id === focusedCase)).sort((a, b) => new Date(a.recorded_at) - new Date(b.recorded_at)), [focusedCase, measurements]);

  async function askAssistant(event) {
    event.preventDefault(); if (!question.trim()) return;
    setAssistantLoading(true); setError("");
    try { const result = await request(`/assistant/explain${caseQuery}`, { method: "POST", body: JSON.stringify({ question: question.trim() }) }); setAnswer(result.answer); }
    catch (requestError) { setError(requestError.message); }
    finally { setAssistantLoading(false); }
  }

  return <div className="app-shell">
    <header className="topbar"><a className="brand" href="#top" aria-label="HMS-cr8 dashboard"><span className="brand-mark">H</span><span><small>HMS-cr8 / monitoring</small><strong>Health signals</strong></span></a>
      <div className="header-center"><span className={`live-indicator ${liveReplay ? "is-live" : ""}`}><i />{liveReplay ? "Live replay" : "Replay paused"}</span><span className="header-divider"/><span className="source-label">{health?.data_source || "VitalDB"} data</span></div>
      <div className="topbar-actions"><button className="icon-button" title="Refresh data" aria-label="Refresh data" onClick={loadDashboard}>↻</button><button className="quiet-button" disabled={replayLoading} onClick={ingestReplay}>{replayLoading ? "Collecting…" : "Ingest window"}</button><button className="quiet-button pause-button" onClick={() => setLiveReplay((active) => !active)}>{liveReplay ? "Pause" : "Resume"}</button></div>
    </header>
    <main id="top" className="dashboard">
      <section className="intro-row"><div><p className="eyebrow">Monitoring workspace</p><h1>Patient overview</h1><p className="intro-copy">Physiological measurements and model output from recorded source data.</p></div><div className="filters">
        <label><span>Case</span><select value={selectedCase} onChange={(event) => setSelectedCase(event.target.value)}><option value="">All cases</option>{cases.map((caseId) => <option key={caseId} value={caseId}>Case {caseId}</option>)}</select></label>
        <label><span>Replay scenario</span><select value={scenario} onChange={(event) => setScenario(event.target.value)}>{scenarios.map((value) => <option key={value} value={value}>{value === "normal" ? "Normal replay" : `Demo: ${value}`}</option>)}</select></label>
      </div></section>
      {error && <div className="notice error-notice" role="alert">{error}</div>}{replayMessage && <div className="notice success-notice" role="status">{replayMessage}</div>}

      <section className="overview-grid">
        <aside className="left-column">
          <article className="panel pulse-panel"><div className="panel-heading"><div><p className="eyebrow">Latest reading</p><h2>Heart rate</h2></div><span className="metric-symbol pulse-symbol">⌁</span></div><strong className="big-reading">{displayValue(latestByMetric["Solar8000/HR"]?.value, latestByMetric["Solar8000/HR"]?.unit)}</strong><span className="reading-time">{latestByMetric["Solar8000/HR"] ? `Recorded ${timeLabel(latestByMetric["Solar8000/HR"].recorded_at, { month: "short", day: "numeric" })}` : "Awaiting measurement"}</span><div className="sparkline"><TrendChart points={heartRatePoints.slice(-28)} /></div></article>
          <article className="panel vitals-panel"><div className="panel-heading"><div><p className="eyebrow">Latest by signal</p><h2>Health metrics</h2></div><span className="subtle-count">{Object.keys(latestByMetric).length} available</span></div>
            {caseMeasurements.length ? <div className="vitals-list">{caseMeasurements.map((row) => <div className="vital-row" key={`${row.case_id}-${row.metric}`}><span className="vital-icon">{row.metric === "Solar8000/HR" ? "⌁" : row.metric === "Solar8000/PLETH_SPO2" ? "◌" : row.metric.includes("NIBP") ? "＋" : row.metric === "Solar8000/BT" ? "°" : "≋"}</span><span className="vital-name">{metricShort[row.metric] || metricName(row.metric)}</span><strong>{displayValue(row.value, row.unit)}</strong></div>)}</div> : <EmptyState title="No readings yet" copy="Recorded measurements will appear here." compact />}
          </article>
          <HeartScore summary={summary} latestByMetric={latestByMetric} />
        </aside>
        <AnatomyPanel metrics={latestByMetric} caseId={focusedCase} />
        <aside className="right-column">
          <article className="panel status-panel"><div className="panel-heading"><div><p className="eyebrow">Analysis status</p><h2>Model output</h2></div><span className={`status-orb ${summary?.status === "attention" ? "attention" : ""}`} /></div><div className="status-main"><StatusBadge status={summary?.status || "insufficient_data"}/><span>{health?.model_loaded ? "Model loaded" : "Model unavailable"}</span></div><div className="status-divider"/><div className="mini-stat-grid"><div><strong>{summary?.anomalies?.length || 0}</strong><span>Active anomalies</span></div><div><strong>{summary?.trend_windows || 0}</strong><span>Feature windows</span></div></div>
            <h3 className="section-caption">Detected anomalies</h3>{summary?.anomalies?.length ? <div className="anomaly-list">{summary.anomalies.slice(0, 3).map((anomaly) => <div className="anomaly-item" key={`${anomaly.case_id}-${anomaly.window_start}`}><span className="anomaly-mark">!</span><span><strong>Review window</strong><small>Case {anomaly.case_id || "unknown"} · {timeLabel(anomaly.window_start, { month: "short", day: "numeric" })}</small></span><b>{Number(anomaly.score).toFixed(2)}</b></div>)}</div> : <p className="quiet-empty">No active anomaly windows reported.</p>}
          </article>
          <article className="panel assistant-panel"><div className="panel-heading"><div><p className="eyebrow">Decision support</p><h2>Ask the health agent</h2></div><span className="agent-badge">AI</span></div><form onSubmit={askAssistant} className="assistant-form"><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What should I review in this case?" maxLength={2000}/><button type="submit" disabled={assistantLoading || !question.trim()}>{assistantLoading ? "Thinking…" : "Ask"}</button></form>{answer ? <div className="assistant-answer">{answer}</div> : <p className="assistant-disclaimer">Explains the available monitoring data and model output. Not a diagnosis or clinical validation.</p>}</article>
        </aside>
      </section>

      <section className="lower-grid"><article className="panel trend-panel"><div className="panel-heading"><div><p className="eyebrow">Recorded measurements</p><h2>Heart rate trend</h2></div><span className="chart-meta">{heartRatePoints.length} readings · {latestByMetric["Solar8000/HR"]?.unit || "unit unavailable"}</span></div><TrendChart points={heartRatePoints}/><p className="chart-footnote">Values and timestamps are shown from the selected case data. No interpolation is applied.</p></article>
        </section>
      <section className="panel feed-panel"><div className="panel-heading"><div><p className="eyebrow">Signal feed</p><h2>Latest measurements</h2></div>{loading && <span className="loading-label">Updating…</span>}</div>{latestMeasurements.length ? <div className="table-wrap"><table><thead><tr><th>Signal</th><th>Value</th><th>Case</th><th>Recorded</th><th>Source</th></tr></thead><tbody>{latestMeasurements.slice(0, 12).map((row, index) => <tr key={`${row.metric}-${row.recorded_at}-${index}`}><td>{metricName(row.metric)}</td><td className="value-cell">{displayValue(row.value, row.unit)}</td><td>{row.case_id}</td><td>{timeLabel(row.recorded_at, { month: "short", day: "numeric" })}</td><td>{row.source || summary?.data_source || "—"}</td></tr>)}</tbody></table></div> : <EmptyState title="No measurements yet" copy="Ingest a VitalDB replay window to populate the monitoring feed."/>}</section>
    </main>
    <footer><span>HMS-cr8</span><span>{summary?.data_source || "VitalDB"} recorded data · anomaly detection support only</span><span>{summary?.generated_at ? `Updated ${timeLabel(summary.generated_at, { month: "short", day: "numeric" })}` : loading ? "Loading data" : "No update timestamp"}</span></footer>
  </div>;
}

function EmptyState({ title, copy, compact = false }) { return <div className={`empty-state ${compact ? "compact" : ""}`}><span className="empty-mark">○</span><strong>{title}</strong><span>{copy}</span></div>; }
export default App;
