import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client.js";
import AuditLog from "../components/AuditLog.jsx";

export default function AuditDetails() {
  const { id } = useParams();
  const [trail, setTrail] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.audit(id).then(setTrail).catch((err) => setError(err.message));
  }, [id]);

  return (
    <>
      <p className="small">
        <Link to="/">← Overview</Link> · <Link to={`/invoices/${id}`}>Invoice detail</Link>
      </p>
      <h1>Audit trail — {id}</h1>
      <p className="muted small">
        Append-only. Each event stores the SHA-256 of the previous one; duplicates are ignored and
        out-of-order arrivals are flagged, never reordered.
      </p>
      {error ? <div className="alert danger">{error}</div> : <AuditLog trail={trail} />}
    </>
  );
}
