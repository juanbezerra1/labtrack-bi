"""`python -m labtrack_bi` does the same as the `labtrack-bi` command."""

import sys

from .cli import main

sys.exit(main())
