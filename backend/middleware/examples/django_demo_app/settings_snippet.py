"""
Day 18 - Django integration example: settings.py snippet.

This file isn't meant to be run - it's reference code. Copy the two
blocks below into your real Django project's settings.py.
"""

# 1) Tell flagkit where the Feature Flag API is and which environment
#    this Django app should read flags from.
FEATURE_FLAG = {
    "BASE_URL": "http://localhost:8000",
    "ENVIRONMENT_ID": 3,       # match an environment_id that exists in your DB (e.g. production)
    "REFRESH_INTERVAL": 30,    # seconds between background cache refreshes
}

# 2) Register the middleware - this builds one shared FlagClient at
#    startup and makes it available as `request.flags` in every view.
#    Add it anywhere after Django's own SessionMiddleware/AuthenticationMiddleware.
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "flagkit.django_middleware.DjangoFlagMiddleware",
    # ...the rest of your middleware
]
