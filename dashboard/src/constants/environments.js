// Single source of truth for environment metadata used across the dashboard.
// Environment CRUD (Day 10 / Milestone 2) will replace this with data fetched
// from a real /environments API — until then, these IDs must match the rows
// seeded into the `environments` table (see root README.md).
export const ENVIRONMENTS = [
  { id: 1, value: "development", label: "Development", color: "#33539E" },
  { id: 2, value: "staging", label: "Staging", color: "#7C6AAE" },
  { id: 3, value: "production", label: "Production", color: "#A5678E" },
];

export function environmentIdForValue(value) {
  return ENVIRONMENTS.find((e) => e.value === value)?.id;
}

export function environmentById(id) {
  return ENVIRONMENTS.find((e) => e.id === id);
}

// {value, label} options, keyed by the string `value` (used by the Navbar's
// environment switcher, which stores "development"/"staging"/"production").
export const ENVIRONMENT_VALUE_OPTIONS = ENVIRONMENTS.map((e) => ({
  value: e.value,
  label: e.label,
}));

// {value, label} options, keyed by numeric `id` (used by the flag Create/Edit
// form, which stores environment_id).
export const ENVIRONMENT_ID_OPTIONS = ENVIRONMENTS.map((e) => ({
  value: e.id,
  label: e.label,
}));