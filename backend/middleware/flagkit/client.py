"""
flagkit - a lightweight Python client/middleware for the Feature Flag
Management System (Day 14).

Consuming applications install this instead of calling the flag API
directly on every request. It fetches the current flag list for one
environment, caches it in memory, and refreshes it periodically on a
background thread - so a hot-path check like `flags.is_enabled(...)`
never blocks on a network call, and keeps working (serving the last
known good values) even if the Feature Flag API is briefly unreachable.

This client caches each flag's basic resolved state (key, enabled,
default_value, type) - the same "simple boolean logic: enabled/disabled
state" scope the evaluation engine started with on Day 4. It does NOT
duplicate the full targeting-rule priority chain (user whitelist / group
targeting / percentage rollout / environment override) on the client
side - that logic lives server-side in evaluation_engine.py, is tested
there, and re-implementing it here would mean keeping two copies of the
same business logic in sync forever. For a fully-resolved, per-user
value that respects targeting rules, call `evaluate(...)`, which hits
the live /flags/evaluate endpoint (and benefits from that endpoint's own
Redis cache on the server side).

Usage:
    from flagkit import FlagClient

    flags = FlagClient(
        api_base_url="http://localhost:8000",
        environment_id=3,
        refresh_interval=30,  # seconds
    )
    flags.start()

    if flags.is_enabled("new_checkout"):
        show_new_flow()
    else:
        show_old_flow()

    flags.stop()  # on app shutdown
"""

import threading
import logging
from typing import Optional, Any

import requests

logger = logging.getLogger("flagkit")


class FlagClient:
    def __init__(
        self,
        api_base_url: str,
        environment_id: int,
        refresh_interval: int = 30,
        request_timeout: float = 3.0,
    ):
        self.api_base_url = api_base_url.rstrip("/")
        self.environment_id = environment_id
        self.refresh_interval = refresh_interval
        self.request_timeout = request_timeout

        self._lock = threading.Lock()
        self._cache: dict[str, dict] = {}
        self._last_refresh_ok = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ---- lifecycle ----

    def start(self):
        """Fetches the initial flag list synchronously (so the very first
        is_enabled() call after start() already has real data, not an
        empty cache), then starts the background refresh thread."""
        self._refresh_once()
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.request_timeout + 1)

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    # ---- background refresh ----

    def _refresh_loop(self):
        while not self._stop_event.wait(self.refresh_interval):
            self._refresh_once()

    def _refresh_once(self):
        try:
            resp = requests.get(
                f"{self.api_base_url}/flags/",
                params={"environment_id": self.environment_id},
                timeout=self.request_timeout,
            )
            resp.raise_for_status()
            flags = resp.json()

            new_cache = {f["key"]: f for f in flags}
            with self._lock:
                self._cache = new_cache
                self._last_refresh_ok = True
            logger.debug("flagkit: refreshed %d flags", len(new_cache))
        except Exception as exc:
            # Fallback to last known good values on API failure - a
            # refresh failure never clears the existing cache, it just
            # leaves it as-is and tries again next interval.
            with self._lock:
                self._last_refresh_ok = False
            logger.warning("flagkit: refresh failed (%s) - serving last known values", exc)

    # ---- reads (thread-safe, in-memory, no network call) ----

    def is_enabled(self, flag_key: str, default: bool = False) -> bool:
        with self._lock:
            flag = self._cache.get(flag_key)
        if flag is None:
            return default
        return bool(flag.get("enabled", default))

    def get_value(self, flag_key: str, default: Any = None) -> Any:
        with self._lock:
            flag = self._cache.get(flag_key)
        if flag is None:
            return default
        return flag.get("default_value", default)

    def get_flag(self, flag_key: str) -> Optional[dict]:
        with self._lock:
            return self._cache.get(flag_key)

    def is_healthy(self) -> bool:
        """False if the last background refresh attempt failed - the
        cache is still being served (last known good values), this just
        tells the caller the data might be stale."""
        with self._lock:
            return self._last_refresh_ok

    # ---- full per-user evaluation (live, not cached) ----

    def evaluate(
        self,
        flag_key: str,
        user_id: Optional[str] = None,
        groups: Optional[list[str]] = None,
        context: Optional[dict] = None,
    ) -> dict:
        """Calls the live /flags/evaluate endpoint for a fully-resolved,
        per-user value that respects targeting rules (whitelist, group,
        rollout, environment override). Unlike is_enabled()/get_value(),
        this always makes a network call - use it when a decision must
        reflect a specific user's targeting, not just the flag's basic
        on/off state."""
        resp = requests.post(
            f"{self.api_base_url}/flags/evaluate",
            json={
                "flag_key": flag_key,
                "environment_id": self.environment_id,
                "user_id": user_id,
                "groups": groups,
                "context": context,
            },
            timeout=self.request_timeout,
        )
        resp.raise_for_status()
        return resp.json()