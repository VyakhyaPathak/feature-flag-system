"""
Day 18 - Django integration for flagkit.

FastAPI apps get a `FlagClient` instance through dependency injection
(see examples/fastapi_demo_app.py) - that doesn't translate directly to
Django, which has no built-in per-request DI container. Django's own
convention for "one shared client, configured from settings.py, used
anywhere" is a middleware that builds it once and a module-level object
views import directly - so that's what this gives you:

    # settings.py
    FEATURE_FLAG = {
        "BASE_URL": "http://localhost:8000",
        "ENVIRONMENT_ID": 3,
        "REFRESH_INTERVAL": 30,
    }
    MIDDLEWARE = [
        ...,
        "flagkit.django_middleware.DjangoFlagMiddleware",
    ]

    # anywhere in the app
    from flagkit import flags
    if flags.is_enabled("beta_banner", user=request.user):
        ...

`DjangoFlagMiddleware` builds a single `FlagClient` from `FEATURE_FLAG`
the first time Django loads it (not per-request - the client's own
background thread handles refreshing) and attaches it to
`request.flags` for convenience. The module-level `flags` proxy below
gives you the same client without needing the request object at all,
which is what most views actually want.
"""
from typing import Optional, Any
from .client import FlagClient


class _LazyFlagsProxy:
    """A stand-in for FlagClient that doesn't exist until Django settings
    are available. `from flagkit import flags` works at import time (module
    load); the real client is built lazily on first use, from
    django.conf.settings.FEATURE_FLAG, and reused after that."""

    def __init__(self):
        self._client: Optional[FlagClient] = None

    def _ensure_client(self) -> FlagClient:
        if self._client is None:
            from django.conf import settings  # imported lazily - flagkit itself has no hard Django dependency

            config = getattr(settings, "FEATURE_FLAG", None)
            if not config or "BASE_URL" not in config or "ENVIRONMENT_ID" not in config:
                raise RuntimeError(
                    "flagkit: settings.FEATURE_FLAG is missing or incomplete. "
                    "Expected at least {'BASE_URL': ..., 'ENVIRONMENT_ID': ...}."
                )
            self._client = FlagClient(
                api_base_url=config["BASE_URL"],
                environment_id=config["ENVIRONMENT_ID"],
                refresh_interval=config.get("REFRESH_INTERVAL", 30),
            ).start()
        return self._client

    def is_enabled(self, flag_key: str, default: bool = False, user=None) -> bool:
        # `user` is accepted (and ignored for the cheap boolean check) purely
        # so view code reads naturally - `flags.is_enabled("x", user=request.user)`.
        # For a value that actually depends on which user is asking, call
        # evaluate(...) instead, which does respect targeting rules.
        return self._ensure_client().is_enabled(flag_key, default=default)

    def get_value(self, flag_key: str, default: Any = None) -> Any:
        return self._ensure_client().get_value(flag_key, default=default)

    def evaluate(self, flag_key: str, user_id: Optional[str] = None, groups=None, context=None) -> dict:
        return self._ensure_client().evaluate(flag_key, user_id=user_id, groups=groups, context=context)

    def is_healthy(self) -> bool:
        return self._ensure_client().is_healthy()


# Import this directly in views: `from flagkit import flags`
flags = _LazyFlagsProxy()


class DjangoFlagMiddleware:
    """Registered in MIDDLEWARE. Doesn't do any per-request flag work
    itself (there's nothing to do - the client refreshes on its own
    background thread) - it just makes sure the shared client exists and
    attaches it to `request.flags` as a convenience for views that
    already have `request` in scope and would rather not add an import."""

    def __init__(self, get_response):
        self.get_response = get_response
        flags._ensure_client()  # fail fast at startup if FEATURE_FLAG is misconfigured, not on the first request

    def __call__(self, request):
        request.flags = flags
        return self.get_response(request)
