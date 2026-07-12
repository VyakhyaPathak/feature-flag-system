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

  useEffect(() => {
    fetchFlag();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flagId]);

  // A flag's detail page is tied to one specific flag ID, which belongs to
  // exactly one environment - it can't "switch" in place. So if the person
  // changes the environment switcher while viewing a flag, send them back to
  // the (environment-aware) Flags list instead of leaving this page showing
  // stale data for the environment they just left.
  //
  // Note: we compare against the *previous actual value* rather than a
  // simple "is this the first render" boolean. React's StrictMode
  // (see main.jsx) intentionally runs effects twice on mount in development;
  // a boolean ref gets flipped by the first pass and then wrongly reads as
  // "changed" on the second pass, triggering a false redirect back to
  // /flags immediately after opening a flag. Comparing actual values is
  // immune to that, since the environment hasn't really changed between
  // those two passes.
  const previousEnvironmentRef = useRef(environment);
  useEffect(() => {
    if (previousEnvironmentRef.current !== environment) {
      navigate("/flags");
    }
    previousEnvironmentRef.current = environment;
  }, [environment, navigate]);

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
        <h3 className="text-sm font-semibold text-gray-900 mb-2">Targeting Rules</h3>
        <p className="text-gray-400 text-sm italic">
          Coming in Milestone 2 — user targeting, group targeting, and percentage rollout rules will appear here.
        </p>
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