"""`python -m figgen 図.yaml` の入口。"""

import sys

from .cli import main

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
