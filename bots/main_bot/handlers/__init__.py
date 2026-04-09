"""
Register all main bot handlers.
Import order matters — text_router must be last (catch-all).
"""
from . import admin      # noqa
from . import sales      # noqa
from . import agronomist # noqa
from . import text_router  # noqa — must be last
