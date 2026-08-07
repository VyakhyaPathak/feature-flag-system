"""
Manual test for the 'fallback to last known good values on API failure'
requirement - proves the SAME client instance keeps serving its last
successfully cached value if the API goes down mid-run, rather than
just showing what happens with an empty cache from a fresh instance.

Run this, then while it's sleeping, go stop uvicorn (Ctrl+C in its
terminal) before the second print happens.
"""

import time
from .client import FlagClient

if __name__ == "__main__":
    flags = FlagClient(
        api_base_url="http://localhost:8000",
        environment_id=3,
        refresh_interval=10,  # short interval so we don't have to wait long
    )
    flags.start()

    print("[t=0s] enabled:", flags.is_enabled("ai_photo_editor"), "| healthy:", flags.is_healthy())
    print(">>> Now STOP uvicorn (Ctrl+C in its terminal) within the next 15 seconds <<<")

    time.sleep(15)  # background thread will attempt a refresh in this window and fail

    print("[t=15s] enabled:", flags.is_enabled("ai_photo_editor"), "| healthy:", flags.is_healthy())
    print("(if 'enabled' printed the same value both times, and 'healthy' flipped to False, the fallback worked)")

    flags.stop()