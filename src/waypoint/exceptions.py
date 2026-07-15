class NotResumableError(Exception):
    """Raised when @checkpoint can't determine how to resume a loop.

    Most commonly this means the loop iterates over a plain generator or
    other non-indexable source -- wrap it with ``waypoint.seq(...)`` or
    convert it to a list first. It's also raised when a checkpoint file on
    disk is unreadable or has an unexpected shape (hand-edited, truncated,
    or written by an incompatible version): resuming from bad state is
    worse than refusing to guess, so @checkpoint fails loudly instead.
    """
