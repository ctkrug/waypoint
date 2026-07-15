class NotResumableError(Exception):
    """Raised when @checkpoint can't determine how to resume a loop.

    Typically means the loop iterates over a plain generator or other
    non-indexable source. Wrap it with ``waypoint.seq(...)`` or convert
    it to a list first.
    """
