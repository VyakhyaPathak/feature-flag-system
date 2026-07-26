import { useState, useEffect } from "react";
import { User, Users, Percent, Globe, Flag as FlagIcon, Check, X, Minus, Zap } from "lucide-react";
import Dropdown from "./Dropdown";
import { getErrorMessage } from "../utils/apiErrors";

const RULE_ICONS = {
  environment_override: { icon: Globe, color: "#33539E" },
  user_whitelist: { icon: User, color: "#33539E" },
  group_targeting: { icon: Users, color: "#33539E" },
  percentage_rollout: { icon: Percent, color: "#33539E" },
  default_value: { icon: FlagIcon, color: "#33539E" },
};

function StatusBadge({ status }) {
  if (status === "matched") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium" style={{ color: "#16A34A" }}>
        <Check size={13} /> Matched
      </span>
    );
  }
  if (status === "no_match") {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-400">
        <X size={13} /> No match
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium text-gray-300">
      <Minus size={13} /> Skipped
    </span>
  );
}

function SourceBadge({ source }) {
  if (source === "cache") {
    return (
      <span
        className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
        style={{ backgroundColor: "rgba(22,163,74,0.1)", color: "#16A34A" }}
      >
        <Zap size={12} /> Cached
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
      style={{ backgroundColor: "rgba(51,83,158,0.1)", color: "#33539E" }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: "#33539E" }}></span> Live
    </span>
  );
}

function EvaluationTestPanel({ flagKey, defaultEnvironmentId }) {
  const [environments, setEnvironments] = useState([]);
  const [envLoading, setEnvLoading] = useState(true);
  const [envError, setEnvError] = useState(null);

  const [environmentId, setEnvironmentId] = useState(defaultEnvironmentId);
  const [userId, setUserId] = useState("");
  const [groupsText, setGroupsText] = useState("");
  const [contextText, setContextText] = useState("");
  const [contextError, setContextError] = useState(null);

  const [evaluating, setEvaluating] = useState(false);
  const [evalError, setEvalError] = useState(null);
  const [result, setResult] = useState(null);

  useEffect(() => {
    setEnvLoading(true);
    setEnvError(null);
    fetch(`http://localhost:8000/environments/`)
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to load environments"));
        return data;
      })
      .then((data) => {
        setEnvironments(data);
        setEnvLoading(false);
      })
      .catch((err) => {
        setEnvError(err.message);
        setEnvLoading(false);
      });
  }, []);

  const handleEvaluate = (e) => {
    e.preventDefault();
    setContextError(null);
    setEvalError(null);

    let parsedContext = null;
    const trimmedContext = contextText.trim();
    if (trimmedContext) {
      try {
        parsedContext = JSON.parse(trimmedContext);
      } catch {
        setContextError('Additional Context must be valid JSON, e.g. {"plan": "premium"}');
        return;
      }
    }

    const groups = groupsText.split(",").map((g) => g.trim()).filter(Boolean);

    setEvaluating(true);
    setResult(null);
    fetch(`http://localhost:8000/flags/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        flag_key: flagKey,
        environment_id: Number(environmentId),
        user_id: userId.trim() || null,
        groups: groups.length ? groups : null,
        context: parsedContext,
      }),
    })
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error(getErrorMessage(data, "Failed to evaluate flag"));
        return data;
      })
      .then((data) => {
        setResult(data);
        setEvaluating(false);
      })
      .catch((err) => {
        setEvalError(err.message);
        setEvaluating(false);
      });
  };

  const envOptions = environments.map((env) => ({ value: env.id, label: env.name }));

  return (
    <div className="border-t border-gray-100 pt-5">
      <h4 className="text-sm font-medium text-gray-800 mb-1">D) Evaluation Test Panel</h4>
      <p className="text-gray-500 text-xs mb-4">
        Test how this flag resolves for a given user &amp; environment, without affecting real
        traffic. "Groups" here are simulated for this test only and always bypass the cache.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <form onSubmit={handleEvaluate} className="space-y-3">
          {envError && <p className="text-red-600 text-xs">{envError}</p>}

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Environment</label>
            <Dropdown
              value={environmentId}
              options={envOptions}
              onChange={setEnvironmentId}
              placeholder={envLoading ? "Loading..." : "Select environment..."}
              disabled={envLoading || environments.length === 0}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">User ID</label>
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="e.g. user_101"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2"
              style={{ "--tw-ring-color": "#33539E" }}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Groups (comma separated)</label>
            <input
              type="text"
              value={groupsText}
              onChange={(e) => setGroupsText(e.target.value)}
              placeholder="beta_users, premium_plan"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2"
              style={{ "--tw-ring-color": "#33539E" }}
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Additional Context (JSON) - reserved for future attribute-based targeting
            </label>
            <textarea
              value={contextText}
              onChange={(e) => setContextText(e.target.value)}
              placeholder={'{\n  "plan": "premium",\n  "country": "IN"\n}'}
              rows={4}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2"
              style={{ "--tw-ring-color": "#33539E" }}
            />
            {contextError && <p className="text-red-600 text-xs mt-1">{contextError}</p>}
          </div>

          {evalError && <p className="text-red-600 text-sm">{evalError}</p>}

          <button
            type="submit"
            disabled={evaluating || envLoading || !environmentId}
            className="px-4 py-2 rounded-lg text-white text-sm font-medium hover:opacity-90 transition disabled:opacity-50"
            style={{ background: "linear-gradient(160deg, #33539E, #A5678E)" }}
          >
            {evaluating ? "Evaluating..." : "▷ Evaluate Flag"}
          </button>
        </form>

        <div>
          {!result ? (
            <p className="text-gray-400 text-sm italic">
              Run an evaluation to see the resolved value and which rule matched.
            </p>
          ) : (
            <div className="space-y-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">Resolved Value</p>
                <div className="flex items-center gap-2">
                  <div
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold"
                    style={{
                      backgroundColor: result.value === true ? "rgba(22,163,74,0.1)" : result.value === false ? "rgba(220,38,38,0.1)" : "rgba(107,114,128,0.1)",
                      color: result.value === true ? "#16A34A" : result.value === false ? "#DC2626" : "#6B7280",
                    }}
                  >
                    {result.value === true ? "TRUE" : result.value === false ? "FALSE" : "N/A"}
                  </div>
                  <SourceBadge source={result.source} />
                </div>
                {typeof result.response_time_ms === "number" && (
                  <p className="text-xs text-gray-400 mt-1">Response time: {result.response_time_ms} ms</p>
                )}
              </div>

              <div>
                <p className="text-xs text-gray-500 mb-1">Matched Rule</p>
                <p className="text-sm font-mono font-semibold" style={{ color: "#33539E" }}>
                  {result.matched_rule.toUpperCase()}
                </p>
              </div>

              {result.rule_detail && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Rule Detail</p>
                  <p className="text-sm text-gray-700">{result.rule_detail}</p>
                </div>
              )}

              <div>
                <p className="text-xs text-gray-500 mb-1">Evaluated At</p>
                <p className="text-sm text-gray-700">{new Date(result.evaluated_at).toLocaleString()}</p>
              </div>

              <div>
                <p className="text-xs text-gray-500 mb-1">Request Summary</p>
                <pre className="text-xs font-mono bg-gray-50 rounded-lg p-2 overflow-x-auto">
                  {JSON.stringify(result.request_summary, null, 2)}
                </pre>
              </div>

              {result.priority_check?.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 mb-2">Priority Check</p>
                  <div className="space-y-1.5">
                    {result.priority_check.map((item, idx) => {
                      const meta = RULE_ICONS[item.rule] || {};
                      const Icon = meta.icon;
                      return (
                        <div
                          key={item.rule}
                          className="flex items-center justify-between rounded-lg px-2.5 py-1.5"
                          style={{ backgroundColor: item.status === "matched" ? "rgba(22,163,74,0.06)" : "transparent" }}
                        >
                          <span className="flex items-center gap-2 text-xs text-gray-700">
                            <span
                              className="flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-semibold text-white"
                              style={{ backgroundColor: meta.color || "#9CA3AF" }}
                            >
                              {idx + 1}
                            </span>
                            {Icon && <Icon size={13} style={{ color: meta.color }} />}
                            {item.label}
                          </span>
                          <StatusBadge status={item.status} />
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default EvaluationTestPanel;