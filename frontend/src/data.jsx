// Dashboard data shared by the Overview, Inbox and Invoices pages and the top nav's waiting count:
// fetched once, polled every 5 s, refreshed after an inbox sync or a decision.
import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { api, AWAITING_HUMAN } from "./api/client.js";

const REFRESH_MS = 5_000;

const DashboardContext = createContext(null);

export function DashboardProvider({ children }) {
  const [summary, setSummary] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [inbox, setInbox] = useState({ status: null, unavailable: false });
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const [s, list] = await Promise.all([api.summary(), api.listInvoices({ limit: 100 })]);
      setSummary(s);
      setInvoices(list.items);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
    try {
      setInbox({ status: await api.inboxStatus(), unavailable: false });
    } catch (err) {
      // 404 = the inbox feature is not on this backend; anything else is a transient error.
      if (err.status === 404) setInbox({ status: null, unavailable: true });
    }
  }, []);

  useEffect(() => {
    load();
    const timer = window.setInterval(load, REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [load]);

  const awaiting = invoices.filter((inv) => AWAITING_HUMAN.includes(inv.status));
  const value = { summary, invoices, inbox, error, load, awaiting };
  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboard() {
  return useContext(DashboardContext);
}
