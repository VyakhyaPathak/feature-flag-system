"""
Day 18 - FastAPI integration example.

A minimal, runnable FastAPI app showing how a real consuming application
wires in the Feature Flag system with only a few lines: build one shared
FlagClient at startup, expose it through a dependency, and call
is_enabled()/evaluate() wherever a flag decision is needed.

Run it (from the `backend` folder, with the main API already running on
port 8000):

    python -m middleware.examples.fastapi_demo_app

Then try:
    curl http://localhost:9000/new-feature
    curl http://localhost:9000/new-feature?user_id=101
    curl http://localhost:9000/health
"""
import sys
import os

# Makes `from flagkit import ...` work no matter what directory this is
# run from - flagkit lives one level up, in backend/middleware/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
import uvicorn

from flagkit import FlagClient

# ---- Configuration ----
# In a real app these come from environment variables / your own config,
# not hardcoded - see the README in backend/middleware/ for the full list.
FLAG_API_BASE_URL = os.environ.get("FLAG_API_BASE_URL", "http://localhost:8000")
FLAG_ENVIRONMENT_ID = int(os.environ.get("FLAG_ENVIRONMENT_ID", "1"))  # match an environment_id that exists in your DB
FLAG_REFRESH_INTERVAL = int(os.environ.get("FLAG_REFRESH_INTERVAL", "30"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # One FlagClient per process, built at startup and reused for every
    # request - not one per request, which would mean a fresh flag fetch
    # (and a cold, empty cache) on every single call.
    app.state.flags = FlagClient(
        api_base_url=FLAG_API_BASE_URL,
        environment_id=FLAG_ENVIRONMENT_ID,
        refresh_interval=FLAG_REFRESH_INTERVAL,
    ).start()
    yield
    app.state.flags.stop()


app = FastAPI(title="Demo App (flagkit integration example)", lifespan=lifespan)


def get_flags(request=None) -> FlagClient:
    """FastAPI dependency - `Depends(get_flags)` in any route gets the
    same shared client `app.state.flags` was built with at startup."""
    return app.state.flags


@app.get("/health")
def health(flags: FlagClient = Depends(get_flags)):
    return {"status": "ok", "flag_cache_healthy": flags.is_healthy()}


@app.get("/new-feature")
def new_feature(user_id: str | None = None, flags: FlagClient = Depends(get_flags)):
    """Cheap, in-memory on/off check - no network call, safe to use on
    every request. Good for a simple kill switch or a flag with no
    per-user targeting."""
    if flags.is_enabled("new_checkout"):
        return {"message": "New Checkout Enabled"}
    return {"message": "Old Flow"}


@app.get("/new-feature-for-me")
def new_feature_for_user(user_id: str, flags: FlagClient = Depends(get_flags)):
    """Full per-user evaluation - respects whitelist/group/percentage
    targeting rules. This always makes a network call (to the flag API's
    own Redis-cached /evaluate endpoint), so use it when the decision
    genuinely depends on who's asking, not for every flag check."""
    result = flags.evaluate("new_checkout", user_id=user_id)
    return {
        "user_id": user_id,
        "enabled": result["value"],
        "reason": result["matched_rule"],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)
