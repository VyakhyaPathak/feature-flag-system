// Capitalizes the first letter for display purposes only.
// The underlying stored/submitted value stays lowercase (e.g. flag.type is
// always "boolean" | "string" | "number" per the backend schema) - this is
// purely so the UI shows "Boolean" instead of "boolean", matching the
// Title Case used by the dropdown options and the rest of the interface.
export function capitalize(str) {
  if (!str) return str;
  return str.charAt(0).toUpperCase() + str.slice(1);
}