import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useEnvironment } from "../context/EnvironmentContext";
import FlagFormModal from "../components/FlagFormModal";
import ConfirmDialog from "../components/ConfirmDialog";
import { ToggleRight, ToggleLeft, ListChecks, Search, Trash2, Zap } from "lucide-react";
import { getErrorMessage } from "../utils/apiErrors";
import { capitalize } from "../utils/format";

function FlagsPage() {
  const { environmentId, environmentName } = useEnvironment();
  const navigate = useNavigate();
  const [flags, setFlags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [fetchError, setFetchError] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [search, setSearch] = useState("");
  const [toast, setToast] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [cacheStatus, setCacheStatus] = useState({});

  const fetchCacheStatus = (list) => {
    const keys = list.map((f) => f.key);
    if (!keys.length) {
      setCacheStatus({});
      return;
    }
    fetch(`http://localhost:8000/flags/cache-status?keys=${encodeURIComponent(keys.join(","))}`)
      .then((res) => res.json())
      .then(setCacheStatus)
      .catch(() => setCacheStatus({}));
  };

  const fetchFlags = () => {
    if (environmentId == null) return;
    setLoading(true);
    setFetchError(null);
    fetch(`http://localhost:8000/flags/?environment_id=${environmentId}`)
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to load flags"));
        return data;
      })
      .then((data) => {
        const list = Array.isArray(data) ? data : [];
        setFlags(list);
        setLoading(false);
        fetchCacheStatus(list);
      })
      .catch((err) => {
        setFetchError(err.message || "Failed to load flags");
        setFlags([]);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchFlags();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [environmentId]);

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
      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(getErrorMessage(errData, "Failed to update flag"));
      }
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

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const res = await fetch(`http://localhost:8000/flags/${deleteTarget.id}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        throw new Error(getErrorMessage(errData, "Failed to delete flag"));
      }
      setFlags((prev) => prev.filter((f) => f.id !== deleteTarget.id));
      setToast({ type: "success", message: `${deleteTarget.key} deleted` });
      setDeleteTarget(null);
    } catch (err) {
      setToast({ type: "error", message: err.message || "Failed to delete flag" });
    } finally {
      setDeleting(false);
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
          Flags — {environmentName || "…"}
        </h2>
        <button
          onClick={() => setShowModal(true)}
          className="text-white px-4 py-2 rounded-lg text-sm font-medium transition hover:opacity-90 shadow-sm"
          style={{ background: "linear-gradient(135deg, #33539E, #A5678E)" }}
        >
          + Create Flag
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
        <div className="brand-card-1 card-hover rounded-xl border shadow-sm p-4 flex items-center gap-3">
          <div
            className="icon-chip w-11 h-11"
            style={{ background: "linear-gradient(160deg, #33539E, #7FACD6)" }}
          >
            <ListChecks size={19} color="white" strokeWidth={2.2} />
          </div>
          <div>
            <p className="text-2xl font-semibold text-gray-900">{flags.length}</p>
            <p className="text-xs text-gray-500">Total Flags</p>
          </div>
        </div>

        <div className="brand-card-2 card-hover rounded-xl border shadow-sm p-4 flex items-center gap-3">
          <div
            className="icon-chip w-11 h-11"
            style={{ background: "linear-gradient(160deg, #7FACD6, #BFB8DA)" }}
          >
            <ToggleRight size={19} color="white" strokeWidth={2.2} />
          </div>
          <div>
            <p className="text-2xl font-semibold text-gray-900">{enabledCount}</p>
            <p className="text-xs text-gray-500">Enabled</p>
          </div>
        </div>

        <div className="brand-card-3 card-hover rounded-xl border shadow-sm p-4 flex items-center gap-3">
          <div
            className="icon-chip w-11 h-11"
            style={{ background: "linear-gradient(160deg, #E8B7D4, #A5678E)" }}
          >
            <ToggleLeft size={19} color="white" strokeWidth={2.2} />
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
          className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2"
          style={{ "--tw-ring-color": "rgba(51,83,158,0.3)" }}
        />
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
        <table className="w-full text-left">
          <thead>
            <tr className="table-header-brand border-b border-gray-200 text-gray-600 text-sm">
              <th className="px-6 py-3 font-medium">Key</th>
              <th className="px-6 py-3 font-medium">Type</th>
              <th className="px-6 py-3 font-medium">Status</th>
              <th className="px-6 py-3 font-medium">Source</th>
              <th className="px-6 py-3 font-medium">Owner</th>
              <th className="px-6 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredFlags.length === 0 ? (
              <tr>
                <td colSpan="6" className="px-6 py-8 text-center text-gray-400 text-sm">
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
                  className="row-hover border-b border-gray-100 last:border-0 cursor-pointer"
                >
                  <td className="px-6 py-4 text-gray-900 font-mono text-sm">{flag.key}</td>
                  <td className="px-6 py-4 text-gray-600 text-sm">
                    <span
                      className="text-xs font-medium px-2 py-0.5 rounded-full"
                      style={{ backgroundColor: "rgba(127,172,214,0.16)", color: "#33539E" }}
                    >
                      {capitalize(flag.type)}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={(e) => handleToggle(flag, e)}
                        className="rounded-full transition relative"
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
                      <span
                        className="text-xs font-medium"
                        style={{ color: flag.enabled ? "var(--success)" : "#9CA3AF" }}
                      >
                        {flag.enabled ? "Live" : "Off"}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    {cacheStatus[flag.key] ? (
                      <span
                        className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
                        style={{ backgroundColor: "rgba(22,163,74,0.1)", color: "#16A34A" }}
                      >
                        <Zap size={11} /> Cached
                      </span>
                    ) : (
                      <span
                        className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
                        style={{ backgroundColor: "rgba(51,83,158,0.1)", color: "#33539E" }}
                      >
                        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#33539E" }}></span> Live
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-gray-600 text-sm">{flag.owner_team || "—"}</td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(flag);
                      }}
                      title="Delete flag"
                      className="p-1.5 rounded-lg text-gray-400 hover:text-white transition"
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#A5678E")}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
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

      {deleteTarget && (
        <ConfirmDialog
          title="Delete this flag?"
          message={`"${deleteTarget.key}" will be permanently deleted from ${environmentName}. This cannot be undone.`}
          confirmLabel="Delete"
          busy={deleting}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setDeleteTarget(null)}
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