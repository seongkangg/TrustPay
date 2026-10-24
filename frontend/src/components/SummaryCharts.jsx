import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// Same hex values as the tokens in styles/dashboard.css so charts and badges agree.
const COLOR = {
  low: "#198038", // --risk-low
  medium: "#b28600", // --risk-medium
  high: "#da1e28", // --risk-high
  blocked: "#da1e28", // --blocked
  ok: "#198038", // --ok
  pending: "#8a3ffc", // --pending
  accent: "#0f62fe", // --accent
  muted: "#5c6670", // --muted
  grid: "#e1e4e8", // --border
};

const STATUS_COLOR = {
  COMPLETED: COLOR.ok,
  APPROVED: COLOR.ok,
  PENDING_APPROVAL: COLOR.pending,
  BLOCKED: COLOR.blocked,
  FAILED: COLOR.blocked,
  REJECTED: COLOR.blocked,
};

const STATUS_ORDER = [
  "RECEIVED",
  "EXTRACTED",
  "VERIFYING",
  "VERIFIED",
  "RISK_REVIEW",
  "PENDING_APPROVAL",
  "APPROVED",
  "COMPLETED",
  "BLOCKED",
  "REJECTED",
  "FAILED",
];

const human = (s) => String(s).replace(/_/g, " ").toLowerCase();
const shortDate = (iso) => iso.slice(5); // "MM-DD"

function Panel({ title, children }) {
  return (
    <div className="chart">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={200}>
        {children}
      </ResponsiveContainer>
    </div>
  );
}

export default function SummaryCharts({ summary }) {
  const risk = ["low", "medium", "high"].map((k) => ({ name: k, count: summary.by_risk[k] ?? 0 }));
  const status = Object.entries(summary.by_status)
    .sort(([a], [b]) => STATUS_ORDER.indexOf(a) - STATUS_ORDER.indexOf(b))
    .map(([name, count]) => ({ name, label: human(name), count }));
  const days = (summary.by_day || []).map((d) => ({ ...d, label: shortDate(d.date) }));

  return (
    <div className="charts">
      <Panel title="Invoices by risk level">
        <BarChart data={risk} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke={COLOR.grid} />
          <XAxis dataKey="name" tickLine={false} axisLine={false} />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
          <Tooltip cursor={{ fill: "#f3f6fb" }} />
          <Bar dataKey="count" name="invoices" radius={[3, 3, 0, 0]}>
            {risk.map((r) => (
              <Cell key={r.name} fill={COLOR[r.name]} />
            ))}
          </Bar>
        </BarChart>
      </Panel>

      <Panel title="Invoices by status">
        <BarChart data={status} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke={COLOR.grid} />
          <XAxis dataKey="label" tickLine={false} axisLine={false} interval={0} />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
          <Tooltip cursor={{ fill: "#f3f6fb" }} />
          <Bar dataKey="count" name="invoices" radius={[3, 3, 0, 0]}>
            {status.map((s) => (
              <Cell key={s.name} fill={STATUS_COLOR[s.name] || COLOR.muted} />
            ))}
          </Bar>
        </BarChart>
      </Panel>

      <Panel title="Last 14 days">
        <LineChart data={days} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke={COLOR.grid} />
          <XAxis dataKey="label" tickLine={false} axisLine={false} minTickGap={16} />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
          <Tooltip />
          <Legend iconType="plainline" />
          <Line type="monotone" dataKey="received" stroke={COLOR.accent} strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="completed" stroke={COLOR.ok} strokeWidth={2} dot={false} />
          <Line type="monotone" dataKey="blocked" stroke={COLOR.blocked} strokeWidth={2} dot={false} />
        </LineChart>
      </Panel>
    </div>
  );
}
