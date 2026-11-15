import { useCallback, useEffect, useMemo, useState } from "react";

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(
  /\/$/,
  "",
);

const metricLabels = {
  "Solar8000/HR": "Heart rate",
  "Solar8000/NIBP_SBP": "Systolic BP",
  "Solar8000/NIBP_DBP": "Diastolic BP",
  "Solar8000/PLETH_SPO2": "SpO₂",
  "Solar8000/BT": "Temperature",
  "Solar8000/RR": "Respiratory rate",
};

const replayTracks = [
  "Solar8000/HR",
  "Solar8000/NIBP_SBP",
  "Solar8000/NIBP_DBP",
  "Solar8000/PLETH_SPO2",
  "Solar8000/BT",
  "Solar8000/RR",
];

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with status ${response.status}`);
  }
  return response.json();
}

function formatMetric(metric) {
  return metricLabels[metric] || metric.replaceAll("/", " / ");
}

function formatValue(value, unit) {
  if (value === null || value === undefined) return "—";
  return `${Number(value).toFixed(1)}${unit ? ` ${unit}` : ""}`;
}

function formatTime(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StatusPill({ status }) {
  const label = status === "attention" ? "Attention" : status || "Unknown";
  return <span className={`status-pill status-${status}`}>{label}</span>;
}

function App() {
  const [health, setHealth] = useState(null);
  const [cases, setCases] = useState([]);
  const [selectedCase, setSelectedCase] = useState("");
  const [summary, setSummary] = useState(null);
  const [measurements, setMeasurements] = useState([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(true);
  const [replayLoading, setReplayLoading] = useState(false);
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [error, setError] = useState("");
  const [replayMessage, setReplayMessage] = useState("");

  const caseQuery = selectedCase
    ? `?case_id=${encodeURIComponent(selectedCase)}`
    : "";

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [healthData, caseData, summaryData, measurementData] =
        await Promise.all([
          request("/health"),
          request("/cases"),
          request(`/health-summary${caseQuery}`),
          request(`/measurements${selectedCase ? `${caseQuery}&` : "?"}limit=100`),
        ]);
      setHealth(healthData);
      setCases(caseData);
      setSummary(summaryData);
      setMeasurements(measurementData);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [caseQuery]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  async function ingestReplay() {
    setReplayLoading(true);
    setError("");
    setReplayMessage("");
    try {
      const latestTimestamp = measurements.reduce((latest, measurement) => {
        if (!latest || measurement.recorded_at > latest) {
          return measurement.recorded_at;
        }
        return latest;
      }, null);
      const nextAt = latestTimestamp
        ? new Date(new Date(latestTimestamp).getTime() + 10_000).toISOString()
        : null;
      const results = await Promise.allSettled(
        replayTracks.map((trackCode) =>
          request("/ingest/vitaldb/replay", {
            method: "POST",
            body: JSON.stringify({
              location: "OR1",
              track_code: trackCode,
              window_seconds: 10,
              ...(nextAt ? { at: nextAt } : {}),
            }),
          }),
        ),
      );
      const successful = results.filter(
        (result) => result.status === "fulfilled",
      );
      const failed = results.filter((result) => result.status === "rejected");
      if (!successful.length) {
        throw new Error(
          "VitalDB replay could not provide any requested physiological tracks.",
        );
      }
      const received = successful.reduce(
        (total, result) => total + result.value.received,
        0,
      );
      setReplayMessage(
        `${received} samples received across ${successful.length} of ${replayTracks.length} tracks${
          failed.length ? `; ${failed.length} unavailable` : ""
        }.`,
      );
      await loadDashboard();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setReplayLoading(false);
    }
  }

  const latestMeasurements = useMemo(
    () =>
      [
        ...(summary?.latest_measurements?.length
          ? summary.latest_measurements
          : measurements),
      ].sort(
        (left, right) =>
          new Date(right.recorded_at) - new Date(left.recorded_at),
      ),
    [measurements, summary],
  );

  async function askAssistant(event) {
    event.preventDefault();
    if (!question.trim()) return;
    setAssistantLoading(true);
    setError("");
    try {
      const result = await request(
        `/assistant/explain${caseQuery}`,
        {
          method: "POST",
          body: JSON.stringify({ question: question.trim() }),
        },
      );
      setAnswer(result.answer);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setAssistantLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">H</div>
          <div>
            <p className="eyebrow">HMS-cr8 / mission control</p>
            <h1>Physiological monitoring</h1>
          </div>
        </div>
        <div className="topbar-actions">
          <span className="source-label">
            <span className="live-dot" />
            VitalDB connected
          </span>
          <button
            className="ghost-button"
            disabled={replayLoading}
            onClick={ingestReplay}
          >
            {replayLoading ? "Collecting..." : "Ingest replay"}
          </button>
        </div>
      </header>

      <main className="dashboard">
        <section className="hero-row">
          <div>
            <p className="eyebrow">Live overview</p>
            <h2>Know what changed.</h2>
            <p className="hero-copy">
              Real-time replay monitoring with case-aware anomaly detection.
            </p>
          </div>
          <label className="case-picker">
            <span>Monitoring case</span>
            <select
              value={selectedCase}
              onChange={(event) => setSelectedCase(event.target.value)}
            >
              <option value="">All cases</option>
              {cases.map((caseId) => (
                <option key={caseId} value={caseId}>
                  Case {caseId}
                </option>
              ))}
            </select>
          </label>
        </section>

        {error && <div className="error-banner">{error}</div>}
        {replayMessage && <div className="success-banner">{replayMessage}</div>}

        <section className="metric-grid">
          <article className="metric-card accent-blue">
            <span className="card-label">System status</span>
            <strong>{health?.status === "ok" ? "Operational" : "Checking"}</strong>
            <span className="card-meta">
              {health?.model_loaded ? "Model loaded" : "Model unavailable"}
            </span>
          </article>
          <article className="metric-card accent-green">
            <span className="card-label">Current analysis</span>
            <strong>
              <StatusPill status={summary?.status || "insufficient_data"} />
            </strong>
            <span className="card-meta">
              {summary?.analysis_status || "Waiting for data"}
            </span>
          </article>
          <article className="metric-card accent-orange">
            <span className="card-label">Measurements</span>
            <strong>{summary?.data_quality?.measurement_count || 0}</strong>
            <span className="card-meta">
              {summary?.data_quality?.metrics_available?.length || 0} metrics available
            </span>
          </article>
          <article className="metric-card accent-red">
            <span className="card-label">Active anomalies</span>
            <strong>{summary?.anomalies?.length || 0}</strong>
            <span className="card-meta">
              {summary?.trend_windows || 0} feature windows analyzed
            </span>
          </article>
        </section>

        <section className="content-grid">
          <article className="panel measurements-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Signal feed</p>
                <h3>Latest measurements</h3>
              </div>
              {loading && <span className="loading-label">Updating...</span>}
            </div>
            {latestMeasurements.length ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Signal</th>
                      <th>Value</th>
                      <th>Case</th>
                      <th>Recorded</th>
                    </tr>
                  </thead>
                  <tbody>
                    {latestMeasurements.slice(0, 12).map((measurement, index) => (
                      <tr key={`${measurement.metric}-${measurement.recorded_at}-${index}`}>
                        <td>{formatMetric(measurement.metric)}</td>
                        <td className="value-cell">
                          {formatValue(measurement.value, measurement.unit)}
                        </td>
                        <td>{measurement.case_id}</td>
                        <td>{formatTime(measurement.recorded_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                title="No measurements yet"
                copy="Ingest a VitalDB replay window to populate the monitoring feed."
              />
            )}
          </article>

          <article className="panel anomaly-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Model output</p>
                <h3>Detected anomalies</h3>
              </div>
              <span className="count-badge">{summary?.anomalies?.length || 0}</span>
            </div>
            {summary?.anomalies?.length ? (
              <div className="anomaly-list">
                {summary.anomalies.map((anomaly) => (
                  <div className="anomaly-item" key={`${anomaly.case_id}-${anomaly.window_start}`}>
                    <div className="anomaly-icon">!</div>
                    <div>
                      <strong>Window requires review</strong>
                      <span>
                        Case {anomaly.case_id || "unknown"} · {formatTime(anomaly.window_start)}
                      </span>
                    </div>
                    <small>{anomaly.score.toFixed(3)}</small>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No active anomalies"
                copy="The current model has not flagged an active window."
                compact
              />
            )}
          </article>
        </section>

        <section className="bottom-grid">
          <article className="panel quality-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Data quality</p>
                <h3>Signal coverage</h3>
              </div>
            </div>
            <div className="signal-tags">
              {(summary?.data_quality?.metrics_available || []).map((metric) => (
                <span className="signal-tag available" key={metric}>
                  <span /> {formatMetric(metric)}
                </span>
              ))}
              {(summary?.data_quality?.expected_metrics_missing || []).map((metric) => (
                <span className="signal-tag missing" key={metric}>
                  <span /> {formatMetric(metric)}
                </span>
              ))}
            </div>
            <p className="quality-note">
              Missing signals are reported explicitly and are not fabricated or
              silently substituted.
            </p>
          </article>

          <article className="panel assistant-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Decision support</p>
                <h3>Ask the health agent</h3>
              </div>
              <span className="agent-badge">AI</span>
            </div>
            <form onSubmit={askAssistant} className="assistant-form">
              <input
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="What should I review in this case?"
                maxLength={2000}
              />
              <button type="submit" disabled={assistantLoading || !question.trim()}>
                {assistantLoading ? "Thinking..." : "Ask"}
              </button>
            </form>
            {answer ? (
              <div className="assistant-answer">{answer}</div>
            ) : (
              <p className="assistant-disclaimer">
                The agent explains monitoring data and model output. It does not
                diagnose conditions or provide clinical validation.
              </p>
            )}
          </article>
        </section>
      </main>
      <footer>
        <span>HMS-cr8</span>
        <span>VitalDB surgical-patient data · anomaly detection support only</span>
      </footer>
    </div>
  );
}

function EmptyState({ title, copy, compact = false }) {
  return (
    <div className={`empty-state ${compact ? "compact" : ""}`}>
      <div className="empty-icon">○</div>
      <strong>{title}</strong>
      <span>{copy}</span>
    </div>
  );
}

export default App;
