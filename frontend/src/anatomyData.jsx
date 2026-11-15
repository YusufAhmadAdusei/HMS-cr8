const metricLabels = {
  "Solar8000/HR": "Heart rate",
  "Solar8000/NIBP_SBP": "Blood pressure",
  "Solar8000/PLETH_SPO2": "SpO₂",
  "Solar8000/RR": "Respiratory rate",
  "Solar8000/BT": "Temperature",
};

export const bodyCallouts = [
  { key: "Solar8000/HR", side: "left", anchor2d: [500, 185], labelY: 175, anchor3d: [0.022, 1.207, 0.03], label3d: [-0.52, 1.36, 0.04] },
  { key: "Solar8000/PLETH_SPO2", side: "right", anchor2d: [528, 178], labelY: 188, anchor3d: [-0.056, 1.188, 0.025], label3d: [0.52, 1.34, 0.03] },
  { key: "Solar8000/NIBP_SBP", side: "right", anchor2d: [548, 235], labelY: 255, anchor3d: [0.09, 1.08, 0.02], label3d: [0.53, 1.04, 0.02] },
  { key: "Solar8000/RR", side: "left", anchor2d: [470, 195], labelY: 225, anchor3d: [0.069, 1.226, 0.025], label3d: [-0.53, 1.14, 0.03] },
  { key: "Solar8000/BT", side: "right", anchor2d: [510, 310], labelY: 340, anchor3d: [0, 1.0, 0.02], label3d: [0.53, 0.82, 0.02] },
];

function valueText(metric, companion) {
  if (!metric) return "—";
  const text = (reading) => {
    const value = Number(reading.value);
    return Number.isInteger(value) ? String(value) : value.toFixed(1);
  };
  if (metric.metric === "Solar8000/NIBP_SBP" && companion) {
    return `${text(metric)} / ${text(companion)}${metric.unit ? ` ${metric.unit}` : ""}`;
  }
  return `${text(metric)}${metric.unit ? ` ${metric.unit}` : ""}`;
}

export function ValueLabel({ item, metrics, className = "", style }) {
  const metric = item.key === "Solar8000/NIBP_SBP"
    ? metrics[item.key] || metrics["Solar8000/NIBP_DBP"]
    : metrics[item.key];
  const diastolic = item.key === "Solar8000/NIBP_SBP" && metric?.metric !== "Solar8000/NIBP_DBP"
    ? metrics["Solar8000/NIBP_DBP"]
    : null;
  const date = metric?.recorded_at
    ? new Date(metric.recorded_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
    : "";
  return <div className={`body-callout ${className}`} style={style}>
    <span>{metricLabels[item.key]}</span>
    <strong>{valueText(metric, diastolic)}</strong>
    {date && <small>{date}</small>}
  </div>;
}
