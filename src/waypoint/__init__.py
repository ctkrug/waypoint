"""waypoint: make any Python loop resumable with one decorator."""

from .core import checkpoint
from .exceptions import NotResumableError
from .sequence import Seq, seq

__version__ = "1.0.0"

__all__ = ["checkpoint", "NotResumableError", "Seq", "seq", "__version__"]
