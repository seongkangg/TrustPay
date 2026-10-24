// Dashboard data shared by the Overview, Inbox and Invoices tabs and the bottom nav: fetched once,
// polled every 15 s, and refreshed on pull-to-refresh or after an inbox sync.
import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { AWAITING_HUMAN, BASE, api } from "./api/client.js";

const REFRESH_MS = 15_000;

const DashboardContext = createContext(null);

export function DashboardProvider({ children }) {
  const [summary, setSummary] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [inbox, setInbox] = useState({ status: null, unavailable: false });
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const [s, list] = await Promise.all([api.summary(), api.listInvoices({ limit: 100 })]);
      setSummary(s);
      setInvoices(list.items);
      setError(null);
    } catch (err) {
      setError(`${err.message} (backend: ${BASE})`);
    }
    try {
      setInbox({ status: await api.inboxStatus(), unavailable: false });
    } catch (err) {
      if (err.status === 404) setInbox({ status: null, unavailable: true });
    }
  }, []);

  useEffect(() => {
    // load() is async: state is set after the fetch resolves, not synchronously in the effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  const awaiting = invoices.filter((inv) => AWAITING_HUMAN.includes(inv.status));
  const value = { summary, invoices, inbox, error, refreshing, refresh, load, awaiting };
  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboard() {
  return useContext(DashboardContext);
}
