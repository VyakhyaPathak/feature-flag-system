import { useEffect, useState } from "react";
import { Server, Database, Zap, AlertCircle } from "lucide-react";

const API_BASE = "http://localhost:8000";

function StatusRow({ icon: Icon, label, status }) {
  const isUp = status === "connected";
  return (
    <div className="flex items-center justify-between py-2">
      <span className="flex items-center gap-2 text-sm text-gray-700">
        <Icon size={15} className="text-gray-400" />
        {label}
      </span>
      <span
        className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-0.5 rounded-full"
        style={{
          backgroundColor: isUp ? "var(--success-bg)" : "var(--danger-bg)",
          color: isUp ? "var(--success)" : "var(--danger)",
        }}
      >
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ backgroundColor: isUp ? "var(--success)" : "var(--danger)" }}
        />
        {isUp ? "Operational" : "Down"}
      </span>
    </div>
  );
}

function SystemStatusPanel() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState(null);

  const fetchHealth = () => {
    fetch(`${API_BASE}/health`)
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        setHealth(data);
        setError(res.ok ? null : "One or more services are unhealthy");
      })
      .catch(() => {
        setError("Could not reach the backend");
        setHealth(null);
      });
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <div className="flex items-center gap-2 mb-2">
        <span
          className="icon-chip w-8 h-8"
          style={{ background: "linear-gradient(160deg, #33539E, #7FACD6)" }}
        >
          <Zap size={15} color="white" strokeWidth={2.4} />
        </span>
        <h3 className="font-semibold text-gray-900 text-sm">System Status</h3>
      </div>
      {error && !health ? (
        <p className="text-xs flex items-center gap-1.5 mt-2" style={{ color: "var(--danger)" }}>
          <AlertCircle size={13} /> {error}
        </p>
      ) : health ? (
        <div className="divide-y divide-gray-50">
          <StatusRow icon={Database} label="PostgreSQL" status={health.postgres} />
          <StatusRow icon={Server} label="Redis" status={health.redis} />
        </div>
      ) : (
        <p className="text-xs text-gray-400 mt-2">Checking...</p>
      )}
    </div>
  );
}

export default SystemStatusPanel;