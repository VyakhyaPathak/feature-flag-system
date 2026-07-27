import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { LayoutDashboard, Flag, Layers } from "lucide-react";
import { useEnvironment } from "../context/EnvironmentContext";
import SystemStatusPanel from "../components/SystemStatusPanel";

const API_BASE = "http://localhost:8000";

function DashboardPage() {
  const { environments, environmentId, environmentName } = useEnvironment();
  const navigate = useNavigate();
  const [flags, setFlags] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (environmentId == null) return;
    setLoading(true);
    fetch(`${API_BASE}/flags/?environment_id=${environmentId}`)
      .then((res) => res.json())
      .then((data) => setFlags(Array.isArray(data) ? data : []))
      .catch(() => setFlags([]))
      .finally(() => setLoading(false));
  }, [environmentId]);

  const enabledCount = flags.filter((f) => f.enabled).length;

  return (
    <div className="p-6">
      <h2 className="text-2xl font-semibold brand-gradient-text mb-6">Dashboard</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="brand-card-1 card-hover rounded-xl border shadow-sm p-4 flex items-center gap-3">
          <div className="icon-chip w-11 h-11" style={{ background: "linear-gradient(160deg, #33539E, #7FACD6)" }}>
            <Flag size={19} color="white" strokeWidth={2.2} />
          </div>
          <div>
            <p className="text-2xl font-semibold text-gray-900">{loading ? "…" : flags.length}</p>
            <p className="text-xs text-gray-500">Flags in {environmentName || "…"}</p>
          </div>
        </div>

        <div className="brand-card-2 card-hover rounded-xl border shadow-sm p-4 flex items-center gap-3">
          <div className="icon-chip w-11 h-11" style={{ background: "linear-gradient(160deg, #7FACD6, #BFB8DA)" }}>
            <Layers size={19} color="white" strokeWidth={2.2} />
          </div>
          <div>
            <p className="text-2xl font-semibold text-gray-900">{environments.length}</p>
            <p className="text-xs text-gray-500">Environments</p>
          </div>
        </div>

        <div className="brand-card-3 card-hover rounded-xl border shadow-sm p-4 flex items-center gap-3">
          <div className="icon-chip w-11 h-11" style={{ background: "linear-gradient(160deg, #E8B7D4, #A5678E)" }}>
            <LayoutDashboard size={19} color="white" strokeWidth={2.2} />
          </div>
          <div>
            <p className="text-2xl font-semibold text-gray-900">{loading ? "…" : enabledCount}</p>
            <p className="text-xs text-gray-500">Enabled in {environmentName || "…"}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SystemStatusPanel />
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4 flex flex-col justify-center items-start gap-2">
          <p className="text-sm font-semibold text-gray-900">Quick Actions</p>
          <button
            onClick={() => navigate("/flags")}
            className="text-sm text-white px-3 py-1.5 rounded-lg hover:opacity-90 transition"
            style={{ background: "linear-gradient(135deg, #33539E, #A5678E)" }}
          >
            Go to Flags →
          </button>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;