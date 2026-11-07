"""Display settings every template can read (chosen on the Settings page, kept in the session)."""

ADVANCED_KEY = "advanced_settings"


def advanced_enabled(request):
    """True when this browser's session has advanced settings on. Off unless set to exactly True."""
    return getattr(request, "session", {}).get(ADVANCED_KEY) is True


def display_settings(request):
    """`advanced`: show the review columns (status, source ID, verification, notes) in full."""
    return {"advanced": advanced_enabled(request)}
