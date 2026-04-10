"""
Register all client bot handlers.
text_router must be last (catch-all).
"""
from .start       import * # noqa
from .orders      import * # noqa
from .profile     import * # noqa
from .faq         import * # noqa
from .text_router import *   # noqa — must be last
