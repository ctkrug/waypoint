---
title: "Waypoint: a decorator that makes any Python loop resumable"
published: false
tags: python, opensource, productivity
---

I keep writing the same throwaway code. A script loops over a few hundred
thousand records, calls a slow API on each one, and runs for an hour. Then
it dies at record 190,000: an OOM, a Ctrl-C, my laptop going to sleep, the
API finally timing out. Rerunning it from the top redoes six figures of
work I already paid for.

The fix everyone reaches for is the same boilerplate: track an index, write
it to a file after each item, read it back at the top, wrap the body in
`try`/`except` so the write actually happens. It works, but it's easy to
get subtly wrong and it buries the one thing the script was supposed to do.

So I wrote [Waypoint](https://github.com/ctkrug/waypoint). The whole API is
one decorator:

```python
from waypoint import checkpoint

@checkpoint
def backfill(records):
    for record in records:
        upload(record)
```

Kill it at record 190,000, rerun the same script, and it resumes at
190,001. Here are the two build decisions I found most interesting.

## Rewriting the loop with AST, not asking the user to

The obvious design is to make people write `for record in resume(records)`.
I didn't want a wrapper in the hot path of every loop. Instead, at
decoration time Waypoint reads the function's own source with
`inspect.getsource`, parses it with `ast`, finds the single top-level
`for` loop, and rewrites just the iterated expression to run through a
small runtime context object. It also appends one `advance()` call as the
loop body's last statement. The body you wrote is otherwise untouched.

The tricky part was closures. Recompiling a function from its AST throws
away the original closure cells, so a function that closes over a helper or
a shared client breaks. The fix: nest the rewritten function inside a
synthetic factory that takes the free variables as parameters, then on
every call re-read the original `func.__closure__` cells and pass their
contents in. Python's compiler wires up fresh cells for the nested
function, and closures keep working.

## The bug that made me add property tests

The first version tracked progress as one integer: "resume at index N." A
reviewer pointed out `continue`. If an early item is skipped with
`continue`, its appended `advance()` never runs, so the running index and
the sequence's true position drift apart. A later item completing in the
same run would then get saved at an index that quietly claimed the skipped
item finished too. On the next run that item is gone, and everything after
it shifts. It silently drops and duplicates records, which is the worst
kind of bug for a tool whose entire promise is "don't lose work."

The fix is small but load-bearing: `advance()` only persists progress that
is contiguous with what's already confirmed done. If a `continue` left a
gap earlier this run, the checkpoint stays put, and the skipped item plus
everything after it is retried next run rather than lost. I backed it with
Hypothesis property tests that assert the core invariant across random
sequences and crash points: every item is processed at least once, in
order, no matter where you kill it. Coverage sits at 99%.

## What I'd do differently

Waypoint deliberately only resumes loops over concrete, sliceable
sequences (`list`, `tuple`, `range`, or anything wrapped in
`waypoint.seq(...)`). A plain generator can't be replayed from an arbitrary
point, so it raises a clear error instead of guessing. If I take it
further, the next steps are cross-call locking (so two processes can share
one job safely) and a chunked mode for loops whose bodies are too fast to
justify an `fsync` per item.

Live page: [apps.charliekrug.com/waypoint](https://apps.charliekrug.com/waypoint/)
Code (MIT): [github.com/ctkrug/waypoint](https://github.com/ctkrug/waypoint)

If you've solved the resumable-loop problem a different way, I'd like to
hear how.
