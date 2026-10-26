// Dashboard data shared by the Overview, Inbox and Invoices tabs and the bottom nav: fetched once,
// polled every 5 s, and refreshed on pull-to-refresh or after an inbox sync.
import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { AWAITING_HUMAN, BASE, api } from "./api/client.js";

const REFRESH_MS = 5_000;
const PROCESSING_REFRESH_MS = 1_500;

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
      console.warn(`load failed (backend: ${BASE})`, err);
      setError(err.message);
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
  }, [load]);

  // While an emailed invoice is being run, check more often so the nav spinner stops promptly.
  const processing = Boolean(inbox.status?.processing);
  useEffect(() => {
    const timer = setInterval(load, processing ? PROCESSING_REFRESH_MS : REFRESH_MS);
    return () => clearInterval(timer);
  }, [load, processing]);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  const awaiting = invoices.filter((inv) => AWAITING_HUMAN.includes(inv.status));
  const value = { summary, invoices, inbox, processing, error, refreshing, refresh, load, awaiting };
  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboard() {
  return useContext(DashboardContext);
}
