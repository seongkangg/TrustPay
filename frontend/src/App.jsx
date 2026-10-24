import { useEffect, useState } from "react";
import { Link, Route, Routes, useLocation } from "react-router-dom";

import { api } from "./api/client.js";
import { ApprovalIcon, HomeIcon, InboxIcon, ListIcon, Mark } from "./components/Icons.jsx";
import AuditDetails from "./pages/AuditDetails.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import InvoiceDetails from "./pages/InvoiceDetails.jsx";

// The overview is one page; the other nav items jump to its sections.
const NAV = [
  { to: "/", hash: "", label: "Overview", Icon: HomeIcon },
  { to: "/#approvals", hash: "#approvals", label: "Approvals", Icon: ApprovalIcon },
  { to: "/#inbox", hash: "#inbox", label: "Inbox", Icon: InboxIcon },
  { to: "/#invoices", hash: "#invoices", label: "Invoices", Icon: ListIcon },
];

function PillNav() {
  const { pathname, hash } = useLocation();
  return (
    <nav className="pillnav" aria-label="Main">
      {NAV.map(({ to, hash: h, label, Icon }) => {
        const active = pathname === "/" && hash === h;
        return (
          <Link
            key={label}
            to={to}
            className={active ? "active" : undefined}
            aria-current={active ? "page" : undefined}
            aria-label={label}
            title={label}
          >
            <Icon />
            <span className="label">{label}</span>
          </Link>
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
    <div className="window">
      <header className="topbar">
        <Link to="/" className="brand">
          <Mark />
          TrustPay
        </Link>
        <PillNav />
        <span className={`health ${health ? (ok ? "up" : "down") : ""}`}>
          <span className="dot" aria-hidden="true" />
          {health ? `Backend ${health.status}${health.llm_mode ? ` · LLM ${health.llm_mode}` : ""}` : "Connecting…"}
        </span>
      </header>
      <main className="page">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/invoices/:id" element={<InvoiceDetails />} />
          <Route path="/invoices/:id/audit" element={<AuditDetails />} />
        </Routes>
      </main>
    </div>
  );
}
