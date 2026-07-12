import { useState } from "react";
import { useEnvironment } from "../context/EnvironmentContext";
import { environmentIdForValue, ENVIRONMENT_ID_OPTIONS } from "../constants/environments";
import Dropdown from "./Dropdown";

const TYPE_OPTIONS = [
  { value: "boolean", label: "Boolean" },
  { value: "string", label: "String" },
  { value: "number", label: "Number" },
];

// FastAPI returns errors in two different shapes:
//  - 400/404/500 from our own routes: { detail: "some readable string" }
//  - 422 from Pydantic validation:    { detail: [{ loc, msg, type, ... }, ...] }
// This turns either shape into one plain, readable sentence for the UI.
function extractErrorMessage(errData, isEditMode) {
  const fallback = `Failed to ${isEditMode ? "update" : "create"} flag`;
  if (!errData || !errData.detail) return fallback;
  if (typeof errData.detail === "string") return errData.detail;
  if (Array.isArray(errData.detail)) {
    const messages = errData.detail
      .map((e) => {
        const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : null;
        return field ? `${field}: ${e.msg}` : e.msg;
      })
      .filter(Boolean);
    return messages.length ? messages.join("; ") : fallback;
  }
  return fallback;
}

function FlagFormModal({ onClose, onFlagCreated, existingFlag = null }) {
  const { environment } = useEnvironment();
  const isEditMode = existingFlag !== null;

  const [key, setKey] = useState(existingFlag?.key || "");
  const [environmentId, setEnvironmentId] = useState(
    existingFlag?.environment_id ?? environmentIdForValue(environment)
  );
  const [type, setType] = useState(existingFlag?.type || "boolean");
  const [defaultValue, setDefaultValue] = useState(existingFlag?.default_value ?? false);
  const [enabled, setEnabled] = useState(existingFlag?.enabled || false);
  const [description, setDescription] = useState(existingFlag?.description || "");
  const [ownerTeam, setOwnerTeam] = useState(existingFlag?.owner_team || "");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      let response;
      if (isEditMode) {
        response = await fetch(`http://localhost:8000/flags/${existingFlag.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            type,
            default_value: defaultValue,
            enabled,
            description,
            owner_team: ownerTeam,
          }),
        });
      } else {
        response = await fetch("http://localhost:8000/flags/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            key,
            environment_id: environmentId,
            type,
            default_value: defaultValue,
            enabled,
            description,
            owner_team: ownerTeam,
          }),
        });
      }

      if (!response.ok) {
        const errData = await response.json().catch(() => null);
        throw new Error(extractErrorMessage(errData, isEditMode));
      }

      onFlagCreated();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const focusStyle = (e) => (e.target.style.boxShadow = "0 0 0 2px rgba(51,83,158,0.25)");
  const blurStyle = (e) => (e.target.style.boxShadow = "none");

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-lg w-full max-w-md overflow-hidden">
        <div
          className="h-1"
          style={{ background: "linear-gradient(160deg, #33539E, #A5678E)" }}
        ></div>
        <div className="p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            {isEditMode ? "Edit Flag" : "Create Flag"}
          </h3>

          {error && (
            <div className="bg-red-50 text-red-700 text-sm px-3 py-2 rounded-lg mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Key</label>
              <input
                type="text"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                onFocus={focusStyle}
                onBlur={blurStyle}
                placeholder="e.g. ai_photo_editor"
                required
                disabled={isEditMode}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none disabled:bg-gray-100 disabled:text-gray-500"
              />
              {isEditMode && (
                <p className="text-xs text-gray-400 mt-1">Key cannot be changed after creation.</p>
              )}
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Environment</label>
              <Dropdown
                value={environmentId}
                options={ENVIRONMENT_ID_OPTIONS}
                onChange={(val) => setEnvironmentId(val)}
                disabled={isEditMode}
              />
              {isEditMode && (
                <p className="text-xs text-gray-400 mt-1">Environment cannot be changed after creation.</p>
              )}
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Type</label>
              <Dropdown value={type} options={TYPE_OPTIONS} onChange={(val) => setType(val)} />
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                onFocus={focusStyle}
                onBlur={blurStyle}
                placeholder="What does this flag control?"
                rows={2}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-600 mb-1">Owner Team</label>
              <input
                type="text"
                value={ownerTeam}
                onChange={(e) => setOwnerTeam(e.target.value)}
                onFocus={focusStyle}
                onBlur={blurStyle}
                placeholder="e.g. ML Team"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none"
              />
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label className="text-sm text-gray-600">Default Value</label>
                <div className="flex items-center gap-2">
                  <span
                    className="text-xs font-medium"
                    style={{ color: defaultValue ? "#33539E" : "#9ca3af" }}
                  >
                    {String(defaultValue)}
                  </span>
                  <button
                    type="button"
                    onClick={() => setDefaultValue(!defaultValue)}
                    className="w-11 h-6 rounded-full transition"
                    style={{ backgroundColor: defaultValue ? "#33539E" : "#d1d5db" }}
                  >
                    <span
                      className={`block w-5 h-5 bg-white rounded-full shadow transform transition ${
                        defaultValue ? "translate-x-5" : "translate-x-0.5"
                      }`}
                    />
                  </button>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label className="text-sm text-gray-600">Enabled</label>
              <div className="flex items-center gap-2">
                <span
                  className="text-xs font-medium"
                  style={{ color: enabled ? "#33539E" : "#9ca3af" }}
                >
                  {enabled ? "Yes" : "No"}
                </span>
                <button
                  type="button"
                  onClick={() => setEnabled(!enabled)}
                  className="w-11 h-6 rounded-full transition"
                  style={{ backgroundColor: enabled ? "#33539E" : "#d1d5db" }}
                >
                  <span
                    className={`block w-5 h-5 bg-white rounded-full shadow transform transition ${
                      enabled ? "translate-x-5" : "translate-x-0.5"
                    }`}
                  />
                </button>
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm rounded-lg transition"
                style={{ color: "#33539E" }}
                onMouseEnter={(e) => (e.target.style.backgroundColor = "rgba(51,83,158,0.06)")}
                onMouseLeave={(e) => (e.target.style.backgroundColor = "transparent")}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-4 py-2 text-sm text-white rounded-lg transition disabled:opacity-50 hover:opacity-90"
                style={{ background: "linear-gradient(160deg, #33539E, #A5678E)" }}
              >
                {submitting ? "Saving..." : isEditMode ? "Save Changes" : "Create Flag"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

export default FlagFormModal;