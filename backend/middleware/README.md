# flagkit - Middleware Integration Guide (Day 18)

`flagkit` is the Python client consuming applications install to read
flags from this system without hand-rolling HTTP calls on every request.
It was built on Day 14; this guide is the "how do I actually wire this
into my app" companion, with runnable examples for both FastAPI and
Django.

## How it works

`FlagClient` fetches the flag list for one environment, caches it in
memory, and refreshes it on a background thread every `refresh_interval`
seconds. Reads (`is_enabled`, `get_value`) never touch the network -
they're plain dict lookups against the in-memory cache. If a refresh
fails (the API is down, network blip, etc.), the client keeps serving
the last known good values instead of erroring or resetting to defaults
- `is_healthy()` tells you if the most recent refresh succeeded, so you
can alert on staleness without breaking traffic.

For decisions that must respect per-user targeting (whitelist / group /
percentage rollout), call `evaluate()` instead - that's a live call to
this system's own `/flags/evaluate` endpoint, which has its own
server-side Redis cache (Day 12).

## Setup

1. Copy `backend/middleware/flagkit/` into your application (or install
   it from a shared internal package index, if you publish one).
2. Install its one dependency: `pip install requests`
3. Build a client once per process and reuse it - see the framework
   examples below.

## Configuration

| Setting | Required | Description |
|---|---|---|
| `api_base_url` | Yes | Base URL of the Feature Flag API, e.g. `http://localhost:8000` |
| `environment_id` | Yes | Which environment this app reads from (Development / Staging / Production) |
| `refresh_interval` | No (default `30`) | Seconds between background cache refreshes |
| `request_timeout` | No (default `3.0`) | Per-request timeout in seconds, for both refresh and `evaluate()` calls |

### Recommended environment variables

Don't hardcode these - read them from the environment so the same code
deploys to every environment unchanged:

```bash
FLAG_API_BASE_URL=https://flags.internal.yourcompany.com
FLAG_ENVIRONMENT_ID=3          # 1=Development, 2=Staging, 3=Production, etc. - match your DB
FLAG_REFRESH_INTERVAL=30
```

## FastAPI example

See `backend/middleware/examples/fastapi_demo_app.py` - fully runnable.
With the main Feature Flag API running on port 8000:

```bash
cd backend
python -m middleware.examples.fastapi_demo_app
```

Then:
```bash
curl http://localhost:9000/new-feature
curl "http://localhost:9000/new-feature-for-me?user_id=101"
curl http://localhost:9000/health
```

The pattern: build one `FlagClient` in the app's `lifespan` (startup),
store it on `app.state`, expose it through a `Depends(...)` dependency.
One client per process, not one per request.

## Django example

See `backend/middleware/examples/django_demo_app/` - reference code
(copy into a real Django project; a runnable Django project isn't part
of this repo since the rest of the stack doesn't use Django).

- `settings_snippet.py` - `FEATURE_FLAG` config block + `MIDDLEWARE` registration
- `views.py` - three usage patterns: `from flagkit import flags` (works anywhere), `request.flags` (via the middleware), and `flags.evaluate(...)` for per-user targeting
- `urls.py` - wires the example views up

The pattern: `DjangoFlagMiddleware` builds one shared client the first
time Django loads it and fails fast at startup if `FEATURE_FLAG` is
misconfigured, rather than failing silently on the first request.

## Best practices

- **One client per process.** Building a `FlagClient` per request means
  every request pays for a fresh (empty) cache and an unnecessary extra
  object - build it once at startup and reuse it.
- **Use `is_enabled()`/`get_value()` for hot paths.** They're in-memory
  lookups - safe to call on every request, even at high traffic.
- **Use `evaluate()` only when you need per-user targeting.** It's a
  live network call; calling it on every request for a flag that
  doesn't actually need per-user logic just adds latency for no benefit.
- **Check `is_healthy()` in your own health check / monitoring**, so a
  silently-stale flag cache (API unreachable for a while) shows up as a
  warning instead of going unnoticed.
- **Call `.stop()` on shutdown** (FastAPI: in `lifespan`'s teardown;
  Django: not needed, the process exiting is enough since it's a daemon
  thread) so the background refresh thread doesn't linger.
- **Pick sensible `default` values** in every `is_enabled()`/`get_value()`
  call - if the flag key doesn't exist yet in this environment (e.g. a
  brand-new flag not yet created here), the default is what gets served,
  not an error.
