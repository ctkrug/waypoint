"""Demo: kill this script with Ctrl-C partway through, then rerun it.

Once @checkpoint's resumable engine lands (docs/BACKLOG.md, Epic 1),
rerunning will skip the items already processed instead of starting
over. For now this demonstrates the intended call shape.
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
