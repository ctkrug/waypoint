"""Demo: kill this script with Ctrl-C partway through, then rerun it.

Rerunning skips the items already processed and resumes right where
the previous run stopped -- no manual save/restore code required.
"""

import time

from waypoint import checkpoint


@checkpoint
def process_all(items):
    for item in items:
        print(f"processing {item}")
        time.sleep(0.2)


if __name__ == "__main__":
    process_all(list(range(50)))
