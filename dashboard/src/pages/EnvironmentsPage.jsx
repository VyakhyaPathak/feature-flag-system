import { useEffect, useState } from "react";
import { Layers, Pencil, Trash2, Plus, X, ToggleLeft } from "lucide-react";
import Dropdown from "../components/Dropdown";
import { getErrorMessage, throwIfNotOk } from "../utils/apiErrors";

const API_BASE = "http://localhost:8000";

function StatusPill({ status }) {
  const isActive = status === "active";
  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-0.5 rounded-full"
      style={{
        backgroundColor: isActive ? "var(--success-bg)" : "rgba(107,114,128,0.1)",
        color: isActive ? "var(--success)" : "#6B7280",
      }}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: isActive ? "var(--success)" : "#9CA3AF" }}
      ></span>
      {isActive ? "Active" : "Inactive"}
    </span>
  );
}

function EnvironmentFormRow({ initial, onSave, onCancel }) {
  const [name, setName] = useState(initial?.name ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [status, setStatus] = useState(initial?.status ?? "active");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleSave = async () => {
    setError(null);
    if (!name.trim()) {
      setError("Name is required");
      return;
    }
    setSaving(true);
    try {
      await onSave({ name: name.trim(), description: description.trim() || null, status });
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <tr style={{ backgroundColor: "rgba(51,83,158,0.04)" }}>
      <td className="px-4 py-2 text-gray-400 text-sm">{initial?.id ?? "—"}</td>
      <td className="px-4 py-2">
        <input
          className="w-full text-sm border border-gray-300 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2"
          style={{ "--tw-ring-color": "rgba(51,83,158,0.3)" }}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. staging"
        />
      </td>
      <td className="px-4 py-2">
        <input
          className="w-full text-sm border border-gray-300 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2"
          style={{ "--tw-ring-color": "rgba(51,83,158,0.3)" }}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional description"
        />
      </td>
      <td className="px-4 py-2">
        <Dropdown
          value={status}
          options={[
            { value: "active", label: "Active" },
            { value: "inactive", label: "Inactive" },
          ]}
          onChange={setStatus}
        />
      </td>
      <td className="px-4 py-2">
        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="text-xs font-medium text-white px-3 py-1.5 rounded-lg hover:opacity-90 transition disabled:opacity-50"
            style={{ background: "linear-gradient(160deg, #33539E, #A5678E)" }}
          >
            {saving ? "Saving..." : "Save"}
          </button>
          <button onClick={onCancel} className="text-gray-400 hover:text-gray-600">
            <X size={16} />
          </button>
        </div>
        {error && <p className="text-xs mt-1" style={{ color: "var(--danger)" }}>{error}</p>}
      </td>
    </tr>
  );
}

function EnvironmentsTable({ environments, onCreate, onUpdate, onDelete }) {
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      <div
        className="h-1.5"
        style={{ background: "linear-gradient(160deg, #33539E, #A5678E)" }}
      ></div>
      <div className="flex justify-between items-center px-5 py-4 border-b border-gray-100">
        <div className="flex items-center gap-2.5">
          <span
            className="icon-chip w-8 h-8"
            style={{ background: "linear-gradient(160deg, #33539E, #7FACD6)" }}
          >
            <Layers size={15} color="white" strokeWidth={2.4} />
          </span>
          <div>
            <h3 className="font-semibold text-gray-900 text-sm">Environments</h3>
            <p className="text-xs text-gray-400">Manage environments and flag overrides.</p>
          </div>
        </div>
        <button
          onClick={() => setCreating(true)}
          className="flex items-center gap-1.5 text-sm font-medium text-white px-3 py-1.5 rounded-lg hover:opacity-90 transition shadow-sm"
          style={{ background: "linear-gradient(135deg, #33539E, #A5678E)" }}
        >
          <Plus size={15} />
          New Environment
        </button>
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="table-header-brand text-left text-gray-500 text-xs uppercase tracking-wide border-b border-gray-100">
            <th className="px-4 py-2.5 font-medium">ID</th>
            <th className="px-4 py-2.5 font-medium">Name</th>
            <th className="px-4 py-2.5 font-medium">Description</th>
            <th className="px-4 py-2.5 font-medium">Status</th>
            <th className="px-4 py-2.5 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {creating && (
            <EnvironmentFormRow
              onSave={async (data) => {
                await onCreate(data);
                setCreating(false);
              }}
              onCancel={() => setCreating(false)}
            />
          )}
          {environments.map((env) =>
            editingId === env.id ? (
              <EnvironmentFormRow
                key={env.id}
                initial={env}
                onSave={async (data) => {
                  await onUpdate(env.id, data);
                  setEditingId(null);
                }}
                onCancel={() => setEditingId(null)}
              />
            ) : (
              <tr key={env.id} className="row-hover border-b border-gray-50 last:border-0">
                <td className="px-4 py-3 text-gray-400">{env.id}</td>
                <td className="px-4 py-3 font-medium text-gray-800 capitalize">{env.name}</td>
                <td className="px-4 py-3 text-gray-500">{env.description || "—"}</td>
                <td className="px-4 py-3">
                  <StatusPill status={env.status} />
                </td>
                <td className="px-4 py-3">
                  {confirmDeleteId === env.id ? (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="text-gray-500">Delete?</span>
                      <button
                        onClick={() => {
                          setDeletingId(env.id);
                          onDelete(env.id).finally(() => {
                            setDeletingId(null);
                            setConfirmDeleteId(null);
                          });
                        }}
                        disabled={deletingId === env.id}
                        className="font-medium hover:opacity-70 disabled:opacity-40"
                        style={{ color: "var(--danger)" }}
                      >
                        {deletingId === env.id ? "Deleting..." : "Confirm"}
                      </button>
                      <button
                        onClick={() => setConfirmDeleteId(null)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => setEditingId(env.id)}
                        className="text-gray-400 transition"
                        onMouseEnter={(e) => (e.currentTarget.style.color = "#33539E")}
                        onMouseLeave={(e) => (e.currentTarget.style.color = "#9CA3AF")}
                        title="Edit"
                      >
                        <Pencil size={15} />
                      </button>
                      <button
                        onClick={() => setConfirmDeleteId(env.id)}
                        className="text-gray-400 hover:text-white p-1 rounded-md transition"
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#A5678E") && (e.currentTarget.style.color = "white")}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent") && (e.currentTarget.style.color = "#9CA3AF")}
                        title="Delete"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            )
          )}
          {environments.length === 0 && !creating && (
            <tr>
              <td colSpan={5} className="px-4 py-8 text-center text-gray-400 text-sm">
                No environments yet — create one to get started.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function OverrideToggle({ checked, onChange, disabled }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      disabled={disabled}
      className="rounded-full transition relative disabled:opacity-50"
      style={{ backgroundColor: checked ? "#33539E" : "#d1d5db", width: "38px", height: "21px" }}
    >
      <span
        className="block bg-white rounded-full shadow transform transition absolute top-0.5"
        style={{ width: "17px", height: "17px", left: checked ? "18px" : "2px" }}
      />
    </button>
  );
}

function FlagOverridesPanel({ flagKeys }) {
  const [selectedKey, setSelectedKey] = useState(null);
  const [overrides, setOverrides] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [savingEnvId, setSavingEnvId] = useState(null);

  useEffect(() => {
    if (flagKeys.length > 0 && !selectedKey) {
      setSelectedKey(flagKeys[0]);
    }
  }, [flagKeys, selectedKey]);

  useEffect(() => {
    if (!selectedKey) return;
    setLoading(true);
    setError(null);
    fetch(`${API_BASE}/flags/by-key/${encodeURIComponent(selectedKey)}/overrides`)
      .then((res) => throwIfNotOk(res, "Failed to load overrides"))
      .then((res) => res.json())
      .then(setOverrides)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [selectedKey]);

  const handleToggle = async (environmentId, nextEnabled) => {
    setSavingEnvId(environmentId);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/flags/by-key/${encodeURIComponent(selectedKey)}/overrides/${environmentId}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ enabled: nextEnabled }),
        }
      );
      await throwIfNotOk(res, "Failed to update override");
      const updated = await res.json();
      setOverrides((prev) => prev.map((o) => (o.environment_id === environmentId ? updated : o)));
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingEnvId(null);
    }
  };

  const handleResetToDefault = async (environmentId) => {
    setSavingEnvId(environmentId);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/flags/by-key/${encodeURIComponent(selectedKey)}/overrides/${environmentId}`,
        { method: "DELETE" }
      );
      await throwIfNotOk(res, "Failed to reset override");
      const updated = await res.json();
      setOverrides((prev) => prev.map((o) => (o.environment_id === environmentId ? updated : o)));
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingEnvId(null);
    }
  };

  const defaultEnabled = overrides[0]?.default_enabled;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden mt-6">
      <div
        className="h-1.5"
        style={{ background: "linear-gradient(160deg, #7FACD6, #A5678E)" }}
      ></div>
      <div className="px-5 py-4 border-b border-gray-100">
        <div className="flex items-center gap-2.5 mb-3">
          <span
            className="icon-chip w-8 h-8"
            style={{ background: "linear-gradient(160deg, #A5678E, #E8B7D4)" }}
          >
            <ToggleLeft size={15} color="white" strokeWidth={2.4} />
          </span>
          <h3 className="font-semibold text-gray-900 text-sm">Flag Overrides by Environment</h3>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-500">Select Flag:</label>
          <Dropdown
            value={selectedKey}
            options={flagKeys.map((k) => ({
              value: k,
              label:
                k === selectedKey && defaultEnabled !== undefined
                  ? `${k} (Default: ${defaultEnabled ? "ON" : "OFF"})`
                  : k,
            }))}
            onChange={setSelectedKey}
          />
        </div>
      </div>

      {error && <p className="text-sm px-5 pt-3" style={{ color: "var(--danger)" }}>{error}</p>}

      {loading ? (
        <p className="text-sm text-gray-400 px-5 py-6">Loading overrides...</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="table-header-brand text-left text-gray-500 text-xs uppercase tracking-wide border-b border-gray-100">
              <th className="px-5 py-2.5 font-medium">Environment</th>
              <th className="px-5 py-2.5 font-medium">Override Value</th>
              <th className="px-5 py-2.5 font-medium">Status</th>
              <th className="px-5 py-2.5 font-medium">Last Updated</th>
              <th className="px-5 py-2.5 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {overrides.map((o) => (
              <tr key={o.environment_id} className="row-hover border-b border-gray-50 last:border-0">
                <td className="px-5 py-3 font-medium text-gray-800 capitalize">{o.environment_name}</td>
                <td className="px-5 py-3">
                  <OverrideToggle
                    checked={o.overridden ? o.override_enabled : o.default_enabled}
                    disabled={savingEnvId === o.environment_id}
                    onChange={(next) => handleToggle(o.environment_id, next)}
                  />
                </td>
                <td className="px-5 py-3">
                  <span
                    className="text-xs font-medium px-2.5 py-0.5 rounded-full"
                    style={
                      o.overridden
                        ? { backgroundColor: "rgba(165,103,142,0.12)", color: "#A5678E" }
                        : { backgroundColor: "rgba(107,114,128,0.1)", color: "#6B7280" }
                    }
                  >
                    {o.overridden ? "Overridden" : "Using Default"}
                  </span>
                </td>
                <td className="px-5 py-3 text-gray-400">
                  {o.updated_at ? new Date(o.updated_at).toLocaleString() : "—"}
                </td>
                <td className="px-5 py-3">
                  {o.overridden && (
                    <button
                      onClick={() => handleResetToDefault(o.environment_id)}
                      disabled={savingEnvId === o.environment_id}
                      className="text-xs text-gray-400 hover:text-gray-700 underline disabled:opacity-50"
                    >
                      Reset to default
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div
        className="mx-5 mb-5 mt-3 text-xs rounded-lg px-4 py-3"
        style={{ backgroundColor: "rgba(51,83,158,0.06)", color: "#33539E" }}
      >
        If an override exists for an environment, that value will be used. Otherwise, the flag's default value will be used.
      </div>
    </div>
  );
}

function EnvironmentsPage() {
  const [environments, setEnvironments] = useState([]);
  const [flagKeys, setFlagKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadEnvironments = () =>
    fetch(`${API_BASE}/environments/`)
      .then((res) => throwIfNotOk(res, "Failed to load environments"))
      .then((res) => res.json())
      .then(setEnvironments);

  const loadFlagKeys = () =>
    fetch(`${API_BASE}/flags/keys`)
      .then((res) => throwIfNotOk(res, "Failed to load flags"))
      .then((res) => res.json())
      .then(setFlagKeys);

  useEffect(() => {
    setLoading(true);
    Promise.all([loadEnvironments(), loadFlagKeys()])
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleCreate = async (data) => {
    const res = await fetch(`${API_BASE}/environments/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    await throwIfNotOk(res, "Failed to create environment");
    await loadEnvironments();
  };

  const handleUpdate = async (id, data) => {
    const res = await fetch(`${API_BASE}/environments/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    await throwIfNotOk(res, "Failed to update environment");
    await loadEnvironments();
  };

  const handleDelete = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/environments/${id}`, { method: "DELETE" });
      await throwIfNotOk(res, "Failed to delete environment");
      await loadEnvironments();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="p-6">
      <h2 className="text-2xl font-semibold brand-gradient-text mb-6">Environments</h2>

      {loading ? (
        <p className="text-gray-400 text-sm">Loading...</p>
      ) : (
        <>
          {error && (
            <p className="text-sm mb-3 px-4 py-2 rounded-lg" style={{ backgroundColor: "var(--danger-bg)", color: "var(--danger)" }}>
              {error}
            </p>
          )}
          <EnvironmentsTable
            environments={environments}
            onCreate={handleCreate}
            onUpdate={handleUpdate}
            onDelete={handleDelete}
          />
          {flagKeys.length > 0 ? (
            <FlagOverridesPanel flagKeys={flagKeys} />
          ) : (
            <p className="text-gray-400 text-sm italic mt-6">
              Create a flag first to configure environment overrides.
            </p>
          )}
        </>
      )}
    </div>
  );
}

export default EnvironmentsPage;