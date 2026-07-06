import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useEnvironment } from "../context/EnvironmentContext";
import FlagFormModal from "../components/FlagFormModal";

function FlagsPage() {
  const { environment } = useEnvironment();
  const navigate = useNavigate();
  const [flags, setFlags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);

  const fetchFlags = () => {
    setLoading(true);
    fetch(`http://localhost:8000/flags/`)
      .then((res) => res.json())
      .then((data) => {
        setFlags(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch flags:", err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchFlags();
  }, [environment]);

  if (loading) {
    return <p className="text-gray-500 p-6">Loading flags...</p>;
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-semibold text-gray-900 capitalize">
          Flags — {environment}
        </h2>
        <button
          onClick={() => setShowModal(true)}
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
        >
          + Create Flag
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-gray-200 text-gray-500 text-sm bg-gray-50">
              <th className="px-6 py-3 font-medium">Key</th>
              <th className="px-6 py-3 font-medium">Type</th>
              <th className="px-6 py-3 font-medium">Status</th>
              <th className="px-6 py-3 font-medium">Owner</th>
            </tr>
          </thead>
          <tbody>
            {flags.map((flag) => (
              <tr
                key={flag.id}
                onClick={() => navigate(`/flags/${flag.id}`)}
                className="border-b border-gray-100 last:border-0 hover:bg-gray-50 transition cursor-pointer"
              >
                <td className="px-6 py-4 text-gray-900 font-mono text-sm">{flag.key}</td>
                <td className="px-6 py-4 text-gray-600 text-sm">{flag.type}</td>
                <td className="px-6 py-4">
                  {flag.enabled ? (
                    <span className="inline-flex items-center gap-1.5 bg-green-50 text-green-700 text-xs font-medium px-2.5 py-1 rounded-full">
                      <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                      Enabled
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 bg-red-50 text-red-700 text-xs font-medium px-2.5 py-1 rounded-full">
                      <span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span>
                      Disabled
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 text-gray-600 text-sm">{flag.owner_team}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showModal && (
        <FlagFormModal
          onClose={() => setShowModal(false)}
          onFlagCreated={fetchFlags}
        />
      )}
    </div>
  );
}

export default FlagsPage;