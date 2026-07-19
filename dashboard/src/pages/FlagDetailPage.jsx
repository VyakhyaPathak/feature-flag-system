import { useState, useEffect, useRef } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import FlagFormModal from "../components/FlagFormModal";
import Dropdown from "../components/Dropdown";
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

  // Targeting rules - A) user whitelist
  const [whitelist, setWhitelist] = useState([]);
  const [whitelistLoading, setWhitelistLoading] = useState(true);
  const [whitelistError, setWhitelistError] = useState(null);
  const [newUserId, setNewUserId] = useState("");
  const [addError, setAddError] = useState(null);
  const [adding, setAdding] = useState(false);
  const [removingId, setRemovingId] = useState(null);

  // Targeting rules - B) group targeting (Day 8)
  const [selectedGroups, setSelectedGroups] = useState([]);
  const [availableGroups, setAvailableGroups] = useState([]);
  const [groupsLoading, setGroupsLoading] = useState(true);
  const [groupsError, setGroupsError] = useState(null);
  const [groupToAdd, setGroupToAdd] = useState("");
  const [addGroupError, setAddGroupError] = useState(null);
  const [addingGroup, setAddingGroup] = useState(false);
  const [removingGroup, setRemovingGroup] = useState(null);

  // Targeting rules - C) percentage rollout (Day 9)
  const [rolloutPercentage, setRolloutPercentage] = useState(0);
  const [rolloutLoading, setRolloutLoading] = useState(true);
  const [rolloutError, setRolloutError] = useState(null);
  const [savingRollout, setSavingRollout] = useState(false);

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

  const fetchGroupTargeting = () => {
    setGroupsLoading(true);
    setGroupsError(null);

    Promise.all([
      fetch(`http://localhost:8000/flags/${flagId}/groups`).then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to load group targeting"));
        return data;
      }),
      fetch(`http://localhost:8000/flags/available-groups`).then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to load available groups"));
        return data;
      }),
    ])
      .then(([selected, available]) => {
        setSelectedGroups(selected);
        setAvailableGroups(available);
        setGroupsLoading(false);
      })
      .catch((err) => {
        setGroupsError(err.message);
        setGroupsLoading(false);
      });
  };

  const fetchRollout = () => {
    setRolloutLoading(true);
    setRolloutError(null);
    fetch(`http://localhost:8000/flags/${flagId}/rollout`)
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to load rollout percentage"));
        return data;
      })
      .then((data) => {
        setRolloutPercentage(data);
        setRolloutLoading(false);
      })
      .catch((err) => {
        setRolloutError(err.message);
        setRolloutLoading(false);
      });
  };

  useEffect(() => {
    fetchFlag();
    fetchWhitelist();
    fetchGroupTargeting();
    fetchRollout();
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

  const handleAddGroup = (groupName) => {
    if (!groupName) return;
    setAddGroupError(null);
    setAddingGroup(true);
    fetch(`http://localhost:8000/flags/${flagId}/groups`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ group_name: groupName }),
    })
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to add group"));
        return data;
      })
      .then((data) => {
        setSelectedGroups(data);
        setGroupToAdd("");
        setAddingGroup(false);
      })
      .catch((err) => {
        setAddGroupError(err.message);
        setAddingGroup(false);
      });
  };

  const handleRemoveGroup = (groupName) => {
    setRemovingGroup(groupName);
    setGroupsError(null);
    fetch(`http://localhost:8000/flags/${flagId}/groups/${encodeURIComponent(groupName)}`, {
      method: "DELETE",
    })
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to remove group"));
        return data;
      })
      .then((data) => {
        setSelectedGroups(data);
        setRemovingGroup(null);
      })
      .catch((err) => {
        setGroupsError(err.message);
        setRemovingGroup(null);
      });
  };

  // The slider updates rolloutPercentage on every drag tick (instant visual
  // feedback, matching the mockup's "Live Effect" behavior), but only
  // PERSISTS to the backend on release (mouseUp/touchEnd/keyUp) - dragging
  // across the full 0-100 range would otherwise fire ~100 API calls in a
  // couple of seconds for no benefit.
  const saveRollout = (value) => {
    setSavingRollout(true);
    setRolloutError(null);
    fetch(`http://localhost:8000/flags/${flagId}/rollout`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ percentage: value }),
    })
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to update rollout percentage"));
        return data;
      })
      .then((data) => {
        setRolloutPercentage(data);
        setSavingRollout(false);
      })
      .catch((err) => {
        setRolloutError(err.message);
        setSavingRollout(false);
        fetchRollout(); // resync with server truth if the save failed
      });
  };

  if (loading) return <p className="text-gray-500 p-6">Loading flag details...</p>;
  if (error) return <p className="text-red-600 p-6">{error}</p>;

  const groupOptions = availableGroups
    .filter((g) => !selectedGroups.includes(g))
    .map((g) => ({ value: g, label: g }));

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
        <h3 className="text-sm font-semibold text-gray-900 mb-4">Targeting Rules</h3>

        {/* A) User Whitelist */}
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-800 mb-1">A) User Whitelist (User IDs)</h4>
          <p className="text-gray-500 text-xs mb-3">
            Users in this list will get the flag enabled.
          </p>

          {whitelistError && <p className="text-red-600 text-sm mb-3">{whitelistError}</p>}

          <form onSubmit={handleAddUserId} className="flex items-start gap-2 mb-3">
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
            <p className="text-gray-400 text-sm">Loading...</p>
          ) : whitelist.length === 0 ? (
            <p className="text-gray-400 text-sm italic">
              No targeting rules yet. All users get the default value.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {whitelist.map((userId) => (
                <span
                  key={userId}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono"
                  style={{ backgroundColor: "rgba(51,83,158,0.08)", color: "#33539E" }}
                >
                  {userId}
                  <button
                    onClick={() => handleRemoveUserId(userId)}
                    disabled={removingId === userId}
                    className="hover:opacity-70 disabled:opacity-40"
                    aria-label={`Remove user ${userId}`}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* B) Group Targeting */}
        <div className="border-t border-gray-100 pt-5 mb-6">
          <h4 className="text-sm font-medium text-gray-800 mb-1">
            B) Group Targeting (Users in selected groups)
          </h4>
          <p className="text-gray-500 text-xs mb-3">
            Users who belong to any of these groups will get the flag enabled.
          </p>

          {groupsError && <p className="text-red-600 text-sm mb-3">{groupsError}</p>}

          {groupsLoading ? (
            <p className="text-gray-400 text-sm">Loading...</p>
          ) : (
            <>
              <div className="mb-3">
                {availableGroups.length === 0 ? (
                  <p className="text-gray-400 text-xs italic">
                    No groups exist yet in user_group_memberships. Add group memberships in the
                    database to make them selectable here.
                  </p>
                ) : groupOptions.length === 0 ? (
                  <p className="text-gray-400 text-xs italic">
                    All available groups are already selected for this flag.
                  </p>
                ) : (
                  <Dropdown
                    value={groupToAdd}
                    options={groupOptions}
                    onChange={(val) => {
                      setGroupToAdd(val);
                      handleAddGroup(val);
                    }}
                    placeholder={addingGroup ? "Adding..." : "Select groups..."}
                    disabled={addingGroup}
                  />
                )}
                {addGroupError && <p className="text-red-600 text-xs mt-1">{addGroupError}</p>}
              </div>

              {selectedGroups.length === 0 ? (
                <p className="text-gray-400 text-sm italic">
                  No groups selected. Group membership won't grant this flag.
                </p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {selectedGroups.map((groupName) => (
                    <span
                      key={groupName}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs"
                      style={{ backgroundColor: "rgba(165,103,142,0.1)", color: "#A5678E" }}
                    >
                      {groupName}
                      <button
                        onClick={() => handleRemoveGroup(groupName)}
                        disabled={removingGroup === groupName}
                        className="hover:opacity-70 disabled:opacity-40"
                        aria-label={`Remove group ${groupName}`}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}

              <p className="text-gray-400 text-xs mt-3">
                Users in ANY selected group will get the flag enabled.
              </p>
            </>
          )}
        </div>

        {/* C) Percentage Rollout */}
        <div className="border-t border-gray-100 pt-5">
          <h4 className="text-sm font-medium text-gray-800 mb-1">C) Percentage Rollout</h4>
          <p className="text-gray-500 text-xs mb-3">
            Gradually enable this flag for a percentage of users.
          </p>

          {rolloutError && <p className="text-red-600 text-sm mb-3">{rolloutError}</p>}

          {rolloutLoading ? (
            <p className="text-gray-400 text-sm">Loading...</p>
          ) : (
            <>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium" style={{ color: "#33539E" }}>
                  Enabled for {rolloutPercentage}% of users.
                  {savingRollout && <span className="text-gray-400 font-normal"> Saving...</span>}
                </p>
                <span
                  className="text-xs font-semibold px-2 py-1 rounded-lg border"
                  style={{ color: "#33539E", borderColor: "#33539E" }}
                >
                  {rolloutPercentage}%
                </span>
              </div>

              <input
                type="range"
                min="0"
                max="100"
                value={rolloutPercentage}
                onChange={(e) => setRolloutPercentage(Number(e.target.value))}
                onMouseUp={(e) => saveRollout(Number(e.target.value))}
                onTouchEnd={(e) => saveRollout(Number(e.target.value))}
                onKeyUp={(e) => saveRollout(Number(e.target.value))}
                disabled={savingRollout}
                className="w-full accent-[#33539E]"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>0%</span>
                <span>100%</span>
              </div>

              <div
                className="mt-4 text-xs rounded-lg px-3 py-2"
                style={{ backgroundColor: "rgba(51,83,158,0.06)", color: "#33539E" }}
              >
                Users are placed into a 0–100 bucket using a deterministic hash of their user ID
                and this flag's key. Users with a bucket below {rolloutPercentage} will see the
                enabled value. Changes take effect immediately — no redeploy needed.
              </div>
            </>
          )}
        </div>
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