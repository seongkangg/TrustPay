import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";

import { api } from "./api/client.js";
import AuditDetails from "./pages/AuditDetails.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import InvoiceDetails from "./pages/InvoiceDetails.jsx";

export default function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({ status: "unreachable" }));
  }, []);

  return (
    <>
      <header className="topbar">
        <span className="brand">TrustPay</span>
        <nav>
          <NavLink to="/" end>
            Overview
          </NavLink>
        </nav>
        <span className="health">
          backend: {health ? `${health.status}${health.llm_mode ? ` · llm ${health.llm_mode}` : ""}` : "…"}
        </span>
      </header>
      <main className="page">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/invoices/:id" element={<InvoiceDetails />} />
          <Route path="/invoices/:id/audit" element={<AuditDetails />} />
        </Routes>
      </main>
    </>
  );
}
