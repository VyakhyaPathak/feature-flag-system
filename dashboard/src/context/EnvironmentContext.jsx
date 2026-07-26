import { createContext, useState, useContext, useEffect, useCallback } from "react";

const API_BASE = "http://localhost:8000";
const EnvironmentContext = createContext();

// Day 10 replaced the hardcoded dev=1/staging=2/prod=3 stub with a real
// Environment CRUD API - this context is now the single place that talks
// to it, so every page (Navbar switcher, Flags list, Flag create form,
// Flag Detail) sees the same live environment list and reacts correctly
// if an environment is renamed, added, or deleted on the Environments page.
export function EnvironmentProvider({ children }) {
  const [environments, setEnvironments] = useState([]);
  const [environmentId, setEnvironmentId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadEnvironments = useCallback(() => {
    setLoading(true);
    setError(null);
    return fetch(`${API_BASE}/environments/`)
      .then(async (res) => {
        const data = await res.json().catch(() => null);
        if (!res.ok) throw new Error("Failed to load environments");
        return data;
      })
      .then((data) => {
        setEnvironments(data);
        // Keep the current selection if it still exists; otherwise fall
        // back to the first environment returned by the API.
        setEnvironmentId((prev) =>
          data.some((e) => e.id === prev) ? prev : (data[0]?.id ?? null)
        );
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    loadEnvironments();
  }, [loadEnvironments]);

  const current = environments.find((e) => e.id === environmentId) || null;

  return (
    <EnvironmentContext.Provider
      value={{
        environments,
        environmentId,
        setEnvironmentId,
        environmentName: current?.name ?? "",
        environmentsLoading: loading,
        environmentsError: error,
        refreshEnvironments: loadEnvironments,
      }}
    >
      {children}
    </EnvironmentContext.Provider>
  );
}

export function useEnvironment() {
  return useContext(EnvironmentContext);
}