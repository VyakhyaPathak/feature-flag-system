import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useEnvironment } from "../context/EnvironmentContext";
import FlagFormModal from "../components/FlagFormModal";
import { ToggleRight, ToggleLeft, ListChecks, Search } from "lucide-react";
import { environmentIdForValue } from "../constants/environments";

function FlagsPage() {
  const { environment } = useEnvironment();
  const navigate = useNavigate();
  const [flags, setFlags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [search, setSearch] = useState("");
  const [toast, setToast] = useState(null);

  const fetchFlags = () => {
    setLoading(true);
    setFetchError(null);
    const environmentId = environmentIdForValue(environment);
    fetch(`http://localhost:8000/flags/?environment_id=${environmentId}`)
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) {
          const message =
            typeof data?.detail === "string" ? data.detail : "Failed to load flags";
          throw new Error(message);
        }
        return data;
      })
      .then((data) => {
        setFlags(Array.isArray(data) ? data : []);
        setLoading(false);
      })
      .catch((err) => {
        setFetchError(err.message || "Failed to load flags");
        setFlags([]);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchFlags();
  }, [environment]);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const handleToggle = async (flag, e) => {
    e.stopPropagation();
    const newEnabled = !flag.enabled;
    try {
      const res = await fetch(`http://localhost:8000/flags/${flag.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: newEnabled }),
      });
      if (!res.ok) throw new Error("Failed to update flag");
      setFlags((prev) =>
        prev.map((f) => (f.id === flag.id ? { ...f, enabled: newEnabled } : f))
      );
      setToast({
        type: "success",
        message: `${flag.key} ${newEnabled ? "enabled" : "disabled"}`,
      });
    } catch (err) {
      setToast({ type: "error", message: err.message || "Failed to update flag" });
    }
  };

  if (loading) {
    return <p className="text-gray-500 p-6">Loading flags...</p>;
  }

  if (fetchError) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-100 text-red-700 text-sm px-4 py-3 rounded-lg flex items-center justify-between">
          <span>{fetchError}</span>
          <button
            onClick={fetchFlags}
            className="text-red-700 font-medium underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const filteredFlags = flags.filter((f) =>
    f.key.toLowerCase().includes(search.toLowerCase())
  );
  const enabledCount = flags.filter((f) => f.enabled).length;
  const disabledCount = flags.length - enabledCount;

  return (
    <div className="p-6 relative">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold brand-gradient-text capitalize">
          Flags — {environment}
        </h2>
        <button
          onClick={() => setShowModal(true)}
          className="text-white px-4 py-2 rounded-lg text-sm font-medium transition hover:opacity-90"
          style={{ background: "linear-gradient(135deg, #33539E, #A5678E)" }}
        >
          + Create Flag
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
  <div className="brand-card-1 rounded-xl border shadow-sm p-4 flex items-center gap-3">
    <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center shadow-sm">
      <ListChecks size={18} style={{ color: "#33539E" }} />
    </div>
    <div>
      <p className="text-2xl font-semibold text-gray-900">{flags.length}</p>
      <p className="text-xs text-gray-500">Total Flags</p>
    </div>
  </div>

  <div className="brand-card-2 rounded-xl border shadow-sm p-4 flex items-center gap-3">
    <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center shadow-sm">
      <ToggleRight size={18} style={{ color: "#7FACD6" }} />
    </div>
    <div>
      <p className="text-2xl font-semibold text-gray-900">{enabledCount}</p>
      <p className="text-xs text-gray-500">Enabled</p>
    </div>
  </div>

  <div className="brand-card-3 rounded-xl border shadow-sm p-4 flex items-center gap-3">
    <div className="w-10 h-10 rounded-lg bg-white flex items-center justify-center shadow-sm">
      <ToggleLeft size={18} style={{ color: "#A5678E" }} />
    </div>
    <div>
      <p className="text-2xl font-semibold text-gray-900">{disabledCount}</p>
      <p className="text-xs text-gray-500">Disabled</p>
    </div>
  </div>
</div>

      <div className="relative mb-4 max-w-xs">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search flags..."
          className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-300"
        />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-gray-200 text-gray-600 text-sm"
            style={{ background: "linear-gradient(135deg, rgba(51,83,158,0.04), rgba(165,103,142,0.04))" }}>
              <th className="px-6 py-3 font-medium">Key</th>
              <th className="px-6 py-3 font-medium">Type</th>
              <th className="px-6 py-3 font-medium">Status</th>
              <th className="px-6 py-3 font-medium">Owner</th>
            </tr>
          </thead>
          <tbody>
            {filteredFlags.length === 0 ? (
              <tr>
                <td colSpan="4" className="px-6 py-8 text-center text-gray-400 text-sm">
                  {flags.length === 0
                    ? 'No flags in this environment yet. Click "+ Create Flag" to add one.'
                    : "No flags match your search."}
                </td>
              </tr>
            ) : (
              filteredFlags.map((flag) => (
                <tr
                  key={flag.id}
                  onClick={() => navigate(`/flags/${flag.id}`)}
                  className="border-b border-gray-100 last:border-0 hover:bg-gray-50 transition cursor-pointer"
                >
                  <td className="px-6 py-4 text-gray-900 font-mono text-sm">{flag.key}</td>
                  <td className="px-6 py-4 text-gray-600 text-sm">{flag.type}</td>
                  <td className="px-6 py-4">
                    <button
                      onClick={(e) => handleToggle(flag, e)}
                      className="w-10 h-5.5 rounded-full transition relative"
                      style={{
                        backgroundColor: flag.enabled ? "#33539E" : "#d1d5db",
                        width: "40px",
                        height: "22px",
                      }}
                    >
                      <span
                        className="block bg-white rounded-full shadow transform transition absolute top-0.5"
                        style={{
                          width: "18px",
                          height: "18px",
                          left: flag.enabled ? "20px" : "2px",
                        }}
                      />
                    </button>
                  </td>
                  <td className="px-6 py-4 text-gray-600 text-sm">{flag.owner_team}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <FlagFormModal
          onClose={() => setShowModal(false)}
          onFlagCreated={() => {
            fetchFlags();
            setToast({ type: "success", message: "Flag created successfully" });
          }}
        />
      )}

      {toast && (
        <div
          className={`fixed bottom-6 right-6 px-4 py-3 rounded-lg shadow-lg text-sm font-medium text-white transition ${
            toast.type === "success" ? "bg-green-600" : "bg-red-600"
          }`}
        >
          {toast.message}
        </div>
      )}
    </div>
  );
}

export default FlagsPage;