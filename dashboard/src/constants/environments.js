// Day 10 introduced a real Environment CRUD API (/environments), so this
// file no longer hardcodes environment ids/names/colors - EnvironmentContext
// fetches the live list instead. The one thing the API doesn't provide is
// a display color, so this just cycles a fixed brand palette by
// environment id, giving each environment a stable, distinct pill color
// on the Flag Detail page without needing to store color in the database.
const PILL_COLORS = ["#33539E", "#7C6AAE", "#A5678E", "#7FACD6", "#E8B7D4"];

export function colorForEnvironmentId(id) {
  if (id == null) return "#6B7280";
  return PILL_COLORS[Math.abs(id) % PILL_COLORS.length];
}