import { useState, useEffect, useRef } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import FlagFormModal from "../components/FlagFormModal";
import { environmentById } from "../constants/environments";
import { useEnvironment } from "../context/EnvironmentContext";
import { getErrorMessage } from "../utils/apiErrors";
import { capitalize } from "../utils/format";

function FlagDetailPage() {
  const { flagId } = useParams();
  const navigate = useNavigate();
  const { environment } = useEnvironment();
  const [flag, setFlag] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);

  // Targeting rules (user whitelist) state
  const [whitelist, setWhitelist] = useState([]);
  const [whitelistLoading, setWhitelistLoading] = useState(true);
  const [whitelistError, setWhitelistError] = useState(null);
  const [newUserId, setNewUserId] = useState("");
  const [addError, setAddError] = useState(null);
  const [adding, setAdding] = useState(false);
  const [removingId, setRemovingId] = useState(null);

  const fetchFlag = () => {
    setLoading(true);
    setError(null);
    fetch(`http://localhost:8000/flags/${flagId}`)
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to load this flag"));
        return data;
      })
      .then((data) => {
        setFlag(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  const fetchWhitelist = () => {
    setWhitelistLoading(true);
    setWhitelistError(null);
    fetch(`http://localhost:8000/flags/${flagId}/whitelist`)
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to load targeting rules"));
        return data;
      })
      .then((data) => {
        setWhitelist(data);
        setWhitelistLoading(false);
      })
      .catch((err) => {
        setWhitelistError(err.message);
        setWhitelistLoading(false);
      });
  };

  useEffect(() => {
    fetchFlag();
    fetchWhitelist();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flagId]);

  const previousEnvironmentRef = useRef(environment);
  useEffect(() => {
    if (previousEnvironmentRef.current !== environment) {
      navigate("/flags");
    }
    previousEnvironmentRef.current = environment;
  }, [environment, navigate]);

  const handleAddUserId = (e) => {
    e.preventDefault();
    setAddError(null);

    const trimmed = newUserId.trim();
    if (!trimmed) {
      setAddError("Please enter a user ID");
      return;
    }
    const parsed = Number(trimmed);
    if (!Number.isInteger(parsed) || parsed <= 0) {
      setAddError("User ID must be a positive whole number");
      return;
    }
    if (whitelist.includes(parsed)) {
      setAddError("This user ID is already whitelisted");
      return;
    }

    setAdding(true);
    fetch(`http://localhost:8000/flags/${flagId}/whitelist`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: parsed }),
    })
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to add user ID"));
        return data;
      })
      .then((data) => {
        setWhitelist(data);
        setNewUserId("");
        setAdding(false);
      })
      .catch((err) => {
        setAddError(err.message);
        setAdding(false);
      });
  };

  const handleRemoveUserId = (userId) => {
    setRemovingId(userId);
    setWhitelistError(null);
    fetch(`http://localhost:8000/flags/${flagId}/whitelist/${userId}`, {
      method: "DELETE",
    })
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to remove user ID"));
        return data;
      })
      .then((data) => {
        setWhitelist(data);
        setRemovingId(null);
      })
      .catch((err) => {
        setWhitelistError(err.message);
        setRemovingId(null);
      });
  };

  if (loading) return <p className="text-gray-500 p-6">Loading flag details...</p>;
  if (error) return <p className="text-red-600 p-6">{error}</p>;

  return (
    <div className="p-6 max-w-2xl">
      <Link to="/flags" className="text-sm hover:underline" style={{ color: "#33539E" }}>
        ← Back to Flags
      </Link>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm mt-4 overflow-hidden">
        <div
          className="h-1"
          style={{ background: "linear-gradient(160deg, #33539E, #A5678E)" }}
        ></div>
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900 font-mono">{flag.key}</h2>
            <div className="flex items-center gap-3">
              {flag.enabled ? (
                <span
                  className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full"
                  style={{ backgroundColor: "rgba(127,172,214,0.15)", color: "#33539E" }}
                >
                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#33539E" }}></span>
                  Enabled
                </span>
              ) : (
                <span
                  className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full"
                  style={{ backgroundColor: "rgba(165,103,142,0.12)", color: "#A5678E" }}
                >
                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#A5678E" }}></span>
                  Disabled
                </span>
              )}
              <button
                onClick={() => setShowEditModal(true)}
                className="px-3 py-1.5 rounded-lg text-white text-sm font-medium hover:opacity-90 transition"
                style={{ background: "linear-gradient(160deg, #33539E, #A5678E)" }}
              >
                Edit Flag
              </button>
            </div>
          </div>

          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-500">Type</dt>
              <dd className="text-gray-900 mt-1">{capitalize(flag.type)}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Default Value</dt>
              <dd className="text-gray-900 mt-1">{flag.default_value ? "True" : "False"}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Owner Team</dt>
              <dd className="text-gray-900 mt-1">{flag.owner_team || "—"}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Environment</dt>
              <dd className="mt-1">
                {(() => {
                  const env = environmentById(flag.environment_id);
                  return (
                    <span
                      className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full"
                      style={{
                        backgroundColor: env ? `${env.color}20` : "#e5e7eb",
                        color: env ? env.color : "#374151",
                      }}
                    >
                      {env ? env.label : `Unknown (id ${flag.environment_id})`}
                    </span>
                  );
                })()}
              </dd>
            </div>
            <div className="col-span-2">
              <dt className="text-gray-500">Description</dt>
              <dd className="text-gray-900 mt-1">{flag.description || "No description provided"}</dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm mt-4 p-6">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-sm font-semibold text-gray-900">Targeting Rules (User Whitelist)</h3>
        </div>
        <p className="text-gray-500 text-xs mb-4">
          Users in this list will get the flag enabled. If the user is not in the list, the default value will be used.
        </p>

        {whitelistError && (
          <p className="text-red-600 text-sm mb-3">{whitelistError}</p>
        )}

        <form onSubmit={handleAddUserId} className="flex items-start gap-2 mb-4">
          <div className="flex-1">
            <input
              type="text"
              value={newUserId}
              onChange={(e) => {
                setNewUserId(e.target.value);
                if (addError) setAddError(null);
              }}
              placeholder="Enter User ID (e.g. 101)"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2"
              style={{ "--tw-ring-color": "#33539E" }}
              disabled={adding}
            />
            {addError && <p className="text-red-600 text-xs mt-1">{addError}</p>}
          </div>
          <button
            type="submit"
            disabled={adding}
            className="px-3 py-2 rounded-lg text-white text-sm font-medium hover:opacity-90 transition disabled:opacity-50"
            style={{ background: "linear-gradient(160deg, #33539E, #A5678E)" }}
          >
            {adding ? "Adding..." : "Add"}
          </button>
        </form>

        {whitelistLoading ? (
          <p className="text-gray-400 text-sm">Loading targeting rules...</p>
        ) : whitelist.length === 0 ? (
          <p className="text-gray-400 text-sm italic">No targeting rules yet. All users get the default value.</p>
        ) : (
          <div>
            <p className="text-xs font-medium text-gray-500 mb-2">
              Whitelisted User IDs ({whitelist.length})
            </p>
            <ul className="space-y-2">
              {whitelist.map((userId) => (
                <li
                  key={userId}
                  className="flex items-center justify-between px-3 py-2 rounded-lg bg-gray-50 border border-gray-100"
                >
                  <span className="text-sm text-gray-900 font-mono">{userId}</span>
                  <button
                    onClick={() => handleRemoveUserId(userId)}
                    disabled={removingId === userId}
                    className="text-xs font-medium text-red-600 hover:text-red-700 disabled:opacity-50"
                  >
                    {removingId === userId ? "Removing..." : "Remove"}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {showEditModal && (
        <FlagFormModal
          existingFlag={flag}
          onClose={() => setShowEditModal(false)}
          onFlagCreated={fetchFlag}
        />
      )}
    </div>
  );
}

export default FlagDetailPage;