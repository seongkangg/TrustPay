import { Area, AreaChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { fmtMoney } from "../api/client.js";

// Same hex values as the tokens in styles/dashboard.css so charts and badges agree.
const COLOR = {
  accent: "#0d9488", // --accent
  accentSoft: "#99ddd3", // --accent-soft
  blocked: "#d92d3a", // --blocked
  muted: "#6b6f7b", // --muted
};

const REDUCED_MOTION =
  typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

// by_day dates are UTC calendar days ("YYYY-MM-DD"); keep them in UTC so the labels never shift.
const utcDate = (iso) => new Date(`${iso}T00:00:00Z`);
const dayLabel = (iso) =>
  utcDate(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" });

function VolumeTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="chart-tip">
      <div className="tip-date">{dayLabel(d.date)}</div>
      <div>
        <span className="key received" /> {d.received} received
      </div>
      <div>
        <span className="key completed" /> {d.completed} completed
      </div>
      {d.blocked > 0 && (
        <div>
          <span className="key blocked" /> {d.blocked} blocked
        </div>
      )}
    </div>
  );
}

// The big chart under the hero figure: invoices received per day, completed as the quiet line.
export function VolumeChart({ days }) {
  const data = days.map((d) => ({ ...d, label: dayLabel(d.date) }));
  return (
    <div className="volume-chart">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 12, right: 4, left: 4, bottom: 0 }}>
          <defs>
            <linearGradient id="volumeFade" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={COLOR.accent} stopOpacity={0.16} />
              <stop offset="100%" stopColor={COLOR.accent} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
            minTickGap={28}
            tick={{ fill: COLOR.muted, fontSize: 11 }}
            dy={6}
          />
          <YAxis hide allowDecimals={false} domain={[0, (max) => Math.max(2, Math.ceil(max * 1.15))]} />
          <Tooltip content={<VolumeTooltip />} cursor={{ stroke: COLOR.accentSoft, strokeWidth: 1 }} />
          <Line
            type="monotone"
            dataKey="completed"
            stroke={COLOR.accentSoft}
            strokeWidth={2}
            dot={false}
            activeDot={false}
            isAnimationActive={!REDUCED_MOTION}
            animationDuration={700}
          />
          <Area
            type="monotone"
            dataKey="received"
            stroke={COLOR.accent}
            strokeWidth={2.5}
            fill="url(#volumeFade)"
            dot={false}
            activeDot={{ r: 4, fill: COLOR.accent, stroke: "#fff", strokeWidth: 2 }}
            isAnimationActive={!REDUCED_MOTION}
            animationDuration={700}
            animationEasing="ease-out"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

// Smooth SVG sparkline for a KPI card. Flat at the baseline when every value is zero.
export function Sparkline({ values, tone = "accent" }) {
  if (values.length < 2) return <div className="sparkline" aria-hidden="true" />;
  const w = 120;
  const h = 32;
  const pad = 3;
  const max = Math.max(1, ...values);
  const step = values.length > 1 ? (w - pad * 2) / (values.length - 1) : 0;
  const pts = values.map((v, i) => [pad + i * step, h - pad - (v / max) * (h - pad * 2)]);
  // Catmull-Rom to cubic Bézier, so the line has the reference's soft curves.
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const [p0, p1, p2, p3] = [pts[i - 1] || pts[i], pts[i], pts[i + 1], pts[i + 2] || pts[i + 1]];
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${c1[0]},${Math.min(h - pad, c1[1])} ${c2[0]},${Math.min(h - pad, c2[1])} ${p2[0]},${p2[1]}`;
  }
  return (
    <svg className={`sparkline ${tone}`} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" aria-hidden="true">
      <path d={d} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

const RISK_LABEL = { low: "Low risk", medium: "Medium risk", high: "High risk" };

// Risk mix as three soft blocks; the high-risk block is the one in colour because it needs eyes.
export function RiskBars({ invoices }) {
  const rows = ["low", "medium", "high"].map((level) => {
    const items = invoices.filter((inv) => inv.risk_level === level);
    return { level, count: items.length, amount: items.reduce((sum, inv) => sum + (inv.amount || 0), 0) };
  });
  const max = Math.max(1, ...rows.map((r) => r.count));
  return (
    <div className="riskbars">
      {rows.map((r) => (
        <div key={r.level} className={`riskbar ${r.level}`}>
          <div className="track">
            <div className="fill" style={{ height: `${Math.max(10, (r.count / max) * 100)}%` }} />
          </div>
          <div className="meta">
            <div className="name">{RISK_LABEL[r.level]}</div>
            <div className="count">
              {r.count} invoice{r.count === 1 ? "" : "s"}
            </div>
            <div className="amount">{fmtMoney(r.amount)}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];

// The last 14 days as a calendar: invoices received per day, today in the accent.
export function DayCalendar({ days }) {
  if (days.length === 0) return null;
  const lead = utcDate(days[0].date).getUTCDay();
  const lastIndex = days.length - 1;
  return (
    <div className="daycal" role="table" aria-label="Invoices received per day, last 14 days">
      {WEEKDAYS.map((w, i) => (
        <div key={`w${i}`} className="wd" role="columnheader">
          {w}
        </div>
      ))}
      {Array.from({ length: lead }, (_, i) => (
        <div key={`pad${i}`} className="cell pad" aria-hidden="true" />
      ))}
      {days.map((d, i) => (
        <div
          key={d.date}
          role="cell"
          className={`cell ${i === lastIndex ? "today" : ""} ${d.received === 0 ? "zero" : ""}`}
          title={`${dayLabel(d.date)}: ${d.received} received, ${d.completed} completed, ${d.blocked} blocked`}
        >
          <span className="date">{utcDate(d.date).getUTCDate()}</span>
          <span className="n">{d.received}</span>
          <span className="sub">{d.blocked > 0 ? `${d.blocked} blocked` : `${d.completed} done`}</span>
        </div>
      ))}
    </div>
  );
}

export { dayLabel };
