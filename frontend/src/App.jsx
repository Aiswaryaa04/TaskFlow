import { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [stats, setStats] = useState(null);
  const [jobType, setJobType] = useState("send_email");
  const [payload, setPayload] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const ws = new WebSocket("ws://127.0.0.1:8001/ws/stats");
    ws.onmessage = (event) => {
      setStats(JSON.parse(event.data));
    };
    ws.onerror = () => {
      setMessage("WebSocket connection failed — is the backend running?");
    };
    return () => ws.close(); // clean up the connection when the component unmounts
  }, []);

  async function submitJob(e) {
    e.preventDefault();
    setMessage("");
    try {
      const res = await fetch("http://127.0.0.1:8001/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_type: jobType, payload }),
      });
      const data = await res.json();
      setMessage(`Job #${data.id} submitted`);
      setPayload("");
    } catch (err) {
      setMessage("Failed to submit job");
    }
  }

  return (
    <div className="app-container">
      <h1 className="app-title">TaskFlow Dashboard</h1>

      <div className="stats-grid">
        <StatCard label="Queue Depth" value={stats?.queue_depth} />
        <StatCard label="Total Jobs" value={stats?.total_jobs} />
        <StatCard label="Completed" value={stats?.completed} color="#4ade80" />
        <StatCard label="Dead Letter" value={stats?.dead_letter_count} color="#f87171" />
      </div>

      <div className="card">
        <h2>Submit a Job</h2>
        <form onSubmit={submitJob}>
          <input
            type="text"
            placeholder="Job type (e.g. send_email)"
            value={jobType}
            onChange={(e) => setJobType(e.target.value)}
            required
          />
          <input
            type="text"
            placeholder="Payload"
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
            required
          />
          <button type="submit">Submit Job</button>
        </form>
        {message && <p className="message">{message}</p>}
      </div>
    </div>
  );
}

function StatCard({ label, value, color = "#818cf8" }) {
  return (
    <div className="stat-card">
      <div className="stat-value" style={{ color }}>
        {value ?? "—"}
      </div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

export default App;