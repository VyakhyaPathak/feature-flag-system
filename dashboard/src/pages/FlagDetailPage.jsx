import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";

function FlagDetailPage() {
  const { flagId } = useParams();
  const [flag, setFlag] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    fetch(`http://localhost:8000/flags/${flagId}`)
      .then((res) => {
        if (!res.ok) throw new Error("Flag not found");
        return res.json();
      })
      .then((data) => {
        setFlag(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [flagId]);

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
          style={{
            background: "linear-gradient(135deg, #33539E, #BFB8DA 50%, #A5678E)",
          }}
        ></div>
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900 font-mono">{flag.key}</h2>
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
          </div>

          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-500">Type</dt>
              <dd className="text-gray-900 mt-1">{flag.type}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Default Value</dt>
              <dd className="text-gray-900 mt-1">{String(flag.default_value)}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Owner Team</dt>
              <dd className="text-gray-900 mt-1">{flag.owner_team || "—"}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Environment ID</dt>
              <dd className="text-gray-900 mt-1">{flag.environment_id}</dd>
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
    </div>
  );
}

export default FlagDetailPage;