"""Load the raw weekly snapshot exports (one CSV per snapshot)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from roche_poc import config

_ENCODINGS = ("utf-8", "utf-8-sig", "latin-1")


def _read_csv(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in _ENCODINGS:
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:  # try the next encoding
            last_error = exc
    raise ValueError(f"Cannot decode {path.name} with {_ENCODINGS}") from last_error


def load_raw_snapshots(raw_dir: Path | str = config.RAW_DIR, pattern: str = "*.csv") -> pd.DataFrame:
    """Concatenate every snapshot CSV found in ``raw_dir``.

    A ``source_file`` column keeps the provenance of each row.
    """
    raw_dir = Path(raw_dir)
    files = sorted(raw_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No file matching {pattern!r} in {raw_dir}")
    frames = []
    for path in files:
        frame = _read_csv(path)
        frame["source_file"] = path.name
        frames.append(frame)
    return pd.concat(frames, ignore_index=True)
