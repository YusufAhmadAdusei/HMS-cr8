import { useEffect, useMemo, useState } from "react";

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const metrics = {
  co2: { label: "CO₂", unit: "ppm", field: "co2_iss" },
  temperature: { label: "Cabin temperature", unit: "°C", field: "temperature_iss" },
  relative_humidity: { label: "Relative humidity", unit: "%", field: "humidity_iss" },
};

function Trend({ rows, metric }) {
  const points = useMemo(() => rows.filter((row) => row.metric === metric)
    .sort((a, b) => Date.parse(a.recorded_at) - Date.parse(b.recorded_at)), [rows, metric]);
  const width = 720, height = 210, left = 48, right = 12, top = 14, bottom = 30;
  if (!points.length) return <div className="chart-empty">No NASA measurements loaded yet.</div>;
  const step = Math.max(1, Math.ceil(points.length / 700));
  const sampled = points.filter((_, index) => index % step === 0 || index === points.length - 1);
  const values = sampled.map((p) => p.value), low = Math.min(...values), high = Math.max(...values);
  const spread = high - low || Math.max(Math.abs(high) * .08, 1);
  const min = low - spread * .12, max = high + spread * .12;
  const x = (i) => left + i * (width - left - right) / Math.max(1, sampled.length - 1);
  const y = (v) => top + (max - v) * (height - top - bottom) / (max - min);
  const line = sampled.map((p, i) => x(i) + "," + y(p.value)).join(" ");
  const ticks = [sampled[0], sampled[Math.floor((sampled.length - 1) / 2)], sampled.at(-1)];
  return <div className="chart-wrap"><svg className="trend-chart" viewBox={"0 0 " + width + " " + height} role="img" aria-label={metrics[metric].label + " historical NASA ISS trend"}>
    {[0, 1, 2].map((tick) => { const yy = top + tick * (height - top - bottom) / 2; const value = max - tick * (max - min) / 2; return <g key={tick}><line x1={left} x2={width - right} y1={yy} y2={yy} className="chart-gridline"/><text x={left - 8} y={yy + 4} textAnchor="end" className="chart-axis">{value.toFixed(0)}</text></g>; })}
    <polyline points={line} className="chart-line"/>
    {ticks.map((point, index) => <text key={index} x={index === 0 ? left : index === 2 ? width - right : width / 2} y={height - 7} textAnchor={index === 0 ? "start" : index === 2 ? "end" : "middle"} className="chart-axis">{new Date(point.recorded_at).toLocaleDateString()}</text>)}
  </svg></div>;
}

export default function EnvironmentalPanel() {
  const [rows, setRows] = useState([]);
  const [metric, setMetric] = useState("co2");
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState("");
  const [dataSource, setDataSource] = useState("NASA EDA API");
  async function load(importWhenEmpty = false) {
    setLoading(true);
    try {
      let response = await fetch(API_URL + "/environmental-measurements?mission=RR-1&limit=50000");
      if (!response.ok) throw new Error("NASA environmental data could not be loaded.");
      let storedRows = await response.json();
      if (importWhenEmpty && storedRows.length === 0) {
        const importResponse = await fetch(API_URL + "/ingest/nasa/eda/RR-1", { method: "POST" });
        if (!importResponse.ok) throw new Error("NASA EDA import failed. Check the backend connection.");
        response = await fetch(API_URL + "/environmental-measurements?mission=RR-1&limit=50000");
        if (!response.ok) throw new Error("NASA data was imported but could not be displayed.");
        storedRows = await response.json();
      }
      setRows(storedRows);
      setDataSource("NASA EDA API · local archive");
      setError("");
    } catch (e) {
      try {
        const response = await fetch("/data/nasa-eda-rr1.json");
        if (!response.ok) throw e;
        const rawRows = await response.json();
        const fields = [
          ["temperature_iss", "temperature", "°C"],
          ["humidity_iss", "relative_humidity", "%"],
          ["co2_iss", "co2", "ppm"],
        ];
        setRows(rawRows.flatMap((row) => fields
          .filter(([field]) => Number.isFinite(row[field]))
          .map(([field, metric, unit]) => ({
            mission: "RR-1",
            recorded_at: row.time,
            metric,
            value: row[field],
            unit,
            source: "NASA OSDR Environmental Data Application",
          }))));
        setDataSource("Bundled NASA EDA reference data");
        setError("");
      } catch { setError(e.message); }
    }
    finally { setLoading(false); }
  }
  async function importNasa() {
    setImporting(true); setError("");
    try {
      const response = await fetch(API_URL + "/ingest/nasa/eda/RR-1", { method: "POST" });
      if (!response.ok) throw new Error("NASA EDA import failed. Check the backend connection.");
      await response.json();
      await load();
    } catch (e) { setError(e.message); }
    finally { setImporting(false); }
  }
  useEffect(() => { load(true); }, []);
  const config = metrics[metric];
  const metricRows = rows.filter((row) => row.metric === metric);
  const latest = metricRows.reduce((a, b) => !a || b.recorded_at > a.recorded_at ? b : a, null);
  return <section className="panel nasa-environment-panel">
    <div className="panel-heading"><div><p className="eyebrow">NASA OSDR · historical ISS data</p><h2>Cabin environment · RR-1</h2><span className="chart-meta">{dataSource}</span></div><button type="button" className="replay-play-button" disabled={importing} onClick={importNasa}>{importing ? "Importing…" : "Refresh NASA data"}</button></div>
    <p className="nasa-context-note">Historical mission context only. RR-1 is a separate 2014 mission; these observations are not live and are not time-aligned with VitalDB recordings.</p>
    <div className="trend-controls"><div className="trend-metric-switch" role="group" aria-label="Select NASA environmental trend">{Object.entries(metrics).map(([key, item]) => <button type="button" key={key} className={metric === key ? "selected" : ""} aria-pressed={metric === key} onClick={() => setMetric(key)}>{item.label}</button>)}</div><span className="chart-meta">{loading ? "Loading stored NASA data…" : metricRows.length ? metricRows.length.toLocaleString() + " samples · " + config.unit + " · " + latest.recorded_at : "No NASA measurements loaded"}</span></div>
    {error && <p className="nasa-context-note" role="alert">{error}</p>}
    {rows.length ? <Trend rows={rows} metric={metric}/> : <div className="chart-empty">{loading ? "Checking locally stored NASA history…" : "Use “Load NASA data” to import the documented NASA EDA RR-1 ISS telemetry series."}</div>}
    <p className="chart-footnote">Source: <a href="https://visualization.osdr.nasa.gov/eda/" target="_blank" rel="noreferrer">NASA OSDR Environmental Data Application</a> · ISS cabin observations only; ground-control data are excluded.</p>
  </section>;
}
