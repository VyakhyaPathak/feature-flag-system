"""
Minimal usage example for flagkit.FlagClient.
See Day 18 for full FastAPI/Django integration examples with a real
consuming application.
"""

from .client import FlagClient

if __name__ == "__main__":
    flags = FlagClient(
        api_base_url="http://localhost:8000",
        environment_id=3,   # production
        refresh_interval=30,
    )
    flags.start()

    try:
        if flags.is_enabled("ai_photo_editor"):
            print("Showing the new AI photo editor flow.")
        else:
            print("Showing the old flow.")

        print("Cache healthy:", flags.is_healthy())

        # Full per-user evaluation, respecting targeting rules:
        result = flags.evaluate("ai_photo_editor", user_id="101")
        print("Evaluated for user 101:", result["value"], "-", result["matched_rule"])
    finally:
        flags.stop()