import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";

import { api } from "./api/client.js";
import { HomeIcon, InboxIcon, ListIcon } from "./components/Icons.jsx";
import { DashboardProvider, useDashboard } from "./data.jsx";
import AuditDetails from "./pages/AuditDetails.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Inbox from "./pages/Inbox.jsx";
import InvoiceDetails from "./pages/InvoiceDetails.jsx";
import Invoices from "./pages/Invoices.jsx";

// The same three pages as the phone app, in a desktop sidebar; Inbox carries the count of invoices
// waiting on a human.
const NAV = [
  { to: "/", label: "Overview", Icon: HomeIcon, end: true },
  { to: "/inbox", label: "Inbox", Icon: InboxIcon, badge: "awaiting" },
  { to: "/invoices", label: "Invoices", Icon: ListIcon },
];

function SideNav() {
  const { awaiting } = useDashboard();
  return (
    <nav className="sidenav" aria-label="Main">
      {NAV.map(({ to, label, Icon, end, badge }) => {
        const count = badge === "awaiting" ? awaiting.length : 0;
        return (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) => (isActive ? "active" : undefined)}
            aria-label={count ? `${label}, ${count} waiting` : label}
          >
            <Icon />
            <span className="label">{label}</span>
            {count > 0 && <span className="nav-badge">{count > 99 ? "99+" : count}</span>}
          </NavLink>
        );
      })}
    </nav>
  );
}

export default function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: "unreachable" }));
  }, []);

  const ok = health?.status === "ok";

  return (
    <DashboardProvider>
      <div className="shell">
        <aside className="sidebar">
          <NavLink to="/" className="brand" aria-label="TrustPay overview">
            <img src="/trustpay-logo.svg" alt="TrustPay" width="131" height="46" />
          </NavLink>
          <SideNav />
          <span className={`health ${health ? (ok ? "up" : "down") : ""}`}>
            <span className="dot" aria-hidden="true" />
            {health ? `Backend ${health.status}${health.llm_mode ? ` · LLM ${health.llm_mode}` : ""}` : "Connecting…"}
          </span>
        </aside>
        <main className="page">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/inbox" element={<Inbox />} />
            <Route path="/invoices" element={<Invoices />} />
            <Route path="/invoices/:id" element={<InvoiceDetails />} />
            <Route path="/invoices/:id/audit" element={<AuditDetails />} />
          </Routes>
        </main>
      </div>
    </DashboardProvider>
  );
}
