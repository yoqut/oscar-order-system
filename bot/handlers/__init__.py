"""
Import all handler modules so their @bot decorators are registered
before any update is processed.
"""
from .common import *          # noqa: F401
from .sales import *           # noqa: F401
from .agronomist import *      # noqa: F401
from .client import *          # noqa: F401
from .admin_handler import *   # noqa: F401
