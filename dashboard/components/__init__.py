"""Reusable dashboard components. Importing this package makes ``roche_poc`` importable
even when the project was not installed with ``pip install -e .``."""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[2] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
