// FastAPI returns errors in two different shapes:
//  - 400/404/500 from our own routes: { detail: "some readable string" }
//  - 422 from Pydantic validation:    { detail: [{ loc, msg, type, ... }, ...] }
// This turns either shape into one plain, readable sentence for the UI.
export function getErrorMessage(errData, fallback = "Something went wrong") {
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

// Reads a fetch Response, and if it's not OK, throws an Error with a
// readable message extracted from the backend's response body.
export async function throwIfNotOk(response, fallback) {
  if (!response.ok) {
    const errData = await response.json().catch(() => null);
    throw new Error(getErrorMessage(errData, fallback));
  }
  return response;
}