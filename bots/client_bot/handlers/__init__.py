"""
Register all client bot handlers.
text_router must be last (catch-all).
"""
from . import start      # noqa
from . import orders     # noqa
from . import profile    # noqa
from . import faq        # noqa
from . import text_router  # noqa — must be last
