import { useState } from "react";
const API = "http://127.0.0.1:8001";
export default function App() {
  const [message, setMessage] = useState(
    "I need to renew my vehicle registration. My insurance expires in 10 days.",
  );
  const [result, setResult] = useState(null),
    [loading, setLoading] = useState(false),
    [error, setError] = useState("");
  async function submit() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const r = await fetch(`${API}/api/requests`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ citizen_id: "demo-citizen", message }),
      });
      const d = await r.json();
      if (!r.ok) throw Error(d.detail || "Request failed");
      setResult(d);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  async function decide(approved) {
    setLoading(true);
    setError("");
    try {
      const r = await fetch(`${API}/api/requests/${result.thread_id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved, comment: "Decision made in demo UI" }),
      });
      const d = await r.json();
      if (!r.ok) throw Error(d.detail || "Resume failed");
      setResult(d);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }
  const s = result?.state || {};
  return (
    <main className="shell">
      <header>
        <div className="mark">C</div>
        <div>
          <small>AGENTIC GOVERNMENT SERVICES</small>
          <h1>CivicOps AI</h1>
        </div>
        <span className="demo">DEMO ENVIRONMENT</span>
      </header>
      <section className="hero">
        <small>CITIZEN SERVICES ASSISTANT</small>
        <h2>How can we help you today?</h2>
        <p>
          Describe your request. Agents retrieve policy evidence, validate your
          profile and prepare an action plan.
        </p>
      </section>
      <section className="panel">
        <label>Your request</label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
        <button
          onClick={submit}
          disabled={loading || message.trim().length < 5}
        >
          {loading ? "Processing…" : "Start agent workflow"}
        </button>
        {error && <p className="error">{error}</p>}
      </section>
      {result && (
        <section className="panel">
          <div className="resultHead">
            <div>
              <small>WORKFLOW RESULT</small>
              <h2>{result.status.replaceAll("_", " ")}</h2>
            </div>
            <span className="pill">{result.status}</span>
          </div>
          <p>{result.response}</p>
          {result.approval_request && (
            <div className="approval">
              <h3>Human approval required</h3>
              <p>{result.approval_request.message}</p>
              <p>
                <b>Vehicle:</b> {result.approval_request.vehicle_id} ·{" "}
                <b>Risk:</b> {result.approval_request.risk_level}
              </p>
              <ol>
                {result.approval_request.action_plan.map((x, i) => (
                  <li key={i}>{x}</li>
                ))}
              </ol>
              <p className="notice">{result.approval_request.notice}</p>
              <button onClick={() => decide(true)} disabled={loading}>
                Approve simulated action
              </button>
              <button
                className="secondary"
                onClick={() => decide(false)}
                disabled={loading}
              >
                Reject
              </button>
            </div>
          )}
          {s.policy_evidence?.length > 0 && (
            <div className="evidence">
              <h3>Retrieved policy evidence</h3>
              {s.policy_evidence.map((x, i) => (
                <article key={i}>
                  <b>{x.title}</b>
                  <small>{x.source}</small>
                  <p>{x.content.slice(0, 360)}…</p>
                </article>
              ))}
            </div>
          )}
          {s.execution_result && (
            <p className="success">
              Simulation reference: <b>{s.execution_result.reference}</b>. No
              government service was contacted.
            </p>
          )}
        </section>
      )}
      <footer>
        LangGraph · FastAPI · React · SQLite <span>Synthetic data only</span>
      </footer>
    </main>
  );
}
