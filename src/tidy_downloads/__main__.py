"""Allow ``python -m tidy_downloads``."""

import sys

from tidy_downloads.cli import main

if __name__ == "__main__":
    sys.exit(main())
