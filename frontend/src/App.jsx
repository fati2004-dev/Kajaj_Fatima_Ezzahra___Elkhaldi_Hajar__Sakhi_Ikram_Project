import { useEffect, useState } from "react";

const api = async (path, options) => {
  const res = await fetch(`/api${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  const data = await res.json();
  if (!res.ok) throw new Error(data?.error?.message || "Erreur API");
  return data;
};

export default function App() {
  const [runs, setRuns] = useState([]);
  const [runId, setRunId] = useState("");
  const [logText, setLogText] = useState("");
  const [env, setEnv] = useState("staging");
  const [incidents, setIncidents] = useState([]);
  const [audit, setAudit] = useState([]);
  const [error, setError] = useState("");

  const refresh = async () => {
    setIncidents(await api("/incidents"));
    setAudit(await api("/audit?limit=15"));
  };

  useEffect(() => {
    api("/runs").then(setRuns).catch((e) => setError(e.message));
    refresh().catch((e) => setError(e.message));
  }, []);

  const run = async (fn) => {
    setError("");
    try { await fn(); await refresh(); } catch (e) { setError(e.message); }
  };

  const analyze = () =>
    run(() => api("/analyze", {
      method: "POST",
      body: JSON.stringify(logText.trim() ? { log_text: logText, environment: env } : { run_id: runId, environment: env }),
    }));

  const decide = (id, verb) => run(() => api(`/incidents/${id}/${verb}`, { method: "POST" }));

  return (
    <main>
      <h1>Agent DevOps</h1>
      <div className="card">
        <h3>Analyser un échec CI/CD</h3>
        <select value={runId} onChange={(e) => setRunId(e.target.value)}>
          <option value="">-- run d'exemple --</option>
          {runs.map((r) => <option key={r}>{r}</option>)}
        </select>{" "}
        <select value={env} onChange={(e) => setEnv(e.target.value)}>
          <option>dev</option><option>staging</option><option>production</option>
        </select>
        <p>ou coller un log :</p>
        <textarea value={logText} onChange={(e) => setLogText(e.target.value)} />
        <button onClick={analyze} disabled={!runId && !logText.trim()}>Analyser</button>
        {error && <span className="err">{error}</span>}
      </div>

      {incidents.map((i) => (
        <div className="card" key={i.id}>
          <b>#{i.id}</b> <span className="badge">{i.diagnosis.category}</span>{" "}
          <span className={`badge ${i.decision.risk}`}>risque : {i.decision.risk}</span>{" "}
          <span className="badge">{i.status}</span>
          <p>{i.diagnosis.explanation} (confiance {Math.round(i.diagnosis.confidence * 100)} %)</p>
          <p><b>Correctif proposé :</b> {i.diagnosis.proposed_fix}</p>
          {i.llm_explanation && <p><i>{i.llm_explanation}</i></p>}
          <pre>{i.diagnosis.evidence.join("\n")}</pre>
          <small>{i.decision.reason}</small>
          {i.status === "awaiting_approval" && (
            <p>
              <button onClick={() => decide(i.id, "approve")}>Approuver ({i.diagnosis.recommended_action})</button>
              <button onClick={() => decide(i.id, "reject")}>Rejeter</button>
            </p>
          )}
        </div>
      ))}

      <div className="card">
        <h3>Journal d'audit</h3>
        <table width="100%"><tbody>
          {audit.map((a, k) => (
            <tr key={k}><td>{a.ts}</td><td>{a.incident_id}</td><td>{a.actor}</td><td>{a.event}</td></tr>
          ))}
        </tbody></table>
      </div>
    </main>
  );
}
