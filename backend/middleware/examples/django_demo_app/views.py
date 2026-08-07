"""
Day 18 - Django integration example: views.py

Reference code - shows the two ways to use flagkit in a Django view once
DjangoFlagMiddleware is registered (see settings_snippet.py).
"""
from django.http import JsonResponse

# Works anywhere, doesn't need `request` in scope - the shared client is
# built once (by the middleware, at startup) and reused for every call.
from flagkit import flags


def checkout_view(request):
    """Cheap, in-memory on/off check - no network call. Good for a
    simple kill switch or a flag with no per-user targeting."""
    if flags.is_enabled("new_checkout", user=request.user):
        return JsonResponse({"message": "New Checkout Enabled"})
    return JsonResponse({"message": "Old Flow"})


def beta_banner_view(request):
    """Same idea, using request.flags (attached by the middleware)
    instead of the imported `flags` proxy - identical client either way,
    just a different way to reach it."""
    if request.flags.is_enabled("beta_banner", user=request.user):
        return JsonResponse({"banner": "You're in the beta!"})
    return JsonResponse({"banner": None})


def checkout_for_user_view(request):
    """Full per-user evaluation - respects whitelist/group/percentage
    targeting rules. Always makes a network call, so use it when the
    decision genuinely depends on who's asking."""
    user_id = str(request.user.id) if request.user.is_authenticated else None
    result = flags.evaluate("new_checkout", user_id=user_id)
    return JsonResponse({
        "user_id": user_id,
        "enabled": result["value"],
        "reason": result["matched_rule"],
    })
