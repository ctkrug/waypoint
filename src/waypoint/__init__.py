"""waypoint: make any Python loop resumable with one decorator."""

from .core import checkpoint
from .exceptions import NotResumableError

__version__ = "0.1.0"

__all__ = ["checkpoint", "NotResumableError", "__version__"]
