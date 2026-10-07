"""Central configuration: paths, column names, domain vocabulary and thresholds.

Everything that was hard-coded in several scripts (file paths, column names,
status labels, alert thresholds) lives here, so that each value has a single
definition that can be justified in the thesis.

No secret is stored in this file: API keys are read from the environment
(see ``.env.example``).
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw" / "Snapshot_2026"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

SNAPSHOTS_PATH = PROCESSED_DIR / "snapshots.parquet"
COMMENTS_PATH = PROCESSED_DIR / "comments.parquet"
TRANSLATION_CACHE_PATH = INTERIM_DIR / "translation_cache.parquet"

# --------------------------------------------------------------------------- #
# Column names (after cleaning)
# --------------------------------------------------------------------------- #
COL_SNAPSHOT = "Snapshot_Date"
COL_MATERIAL = "MATERIAL_NUMBER"
COL_MATERIAL_DESC = "MATERIAL_DESC"
COL_VENDOR = "VENDOR_NAME"
COL_VENDOR_ID = "VENDOR_ACCOUNT_NUMBER"
COL_MRP = "MRP_CONTROLLER"
COL_STATUS = "MATERIAL_STATUS"
COL_IMPACT = "Impact"
COL_ROOT_CAUSE = "Root_Cause"
COL_COMMENT = "Comment"          # cleaned original text (EN or DE)
COL_COMMENT_EN = "Comment_EN"    # English version (translated when needed)
COL_LANGUAGE = "comment_language"
COL_STOCKOUT_DATE = "STOCKOUT_DATE"
COL_DELAY = "Delay"

# Raw column names that are renamed during cleaning.
RAW_RENAMES = {"Issue": COL_ROOT_CAUSE, "comment": COL_COMMENT}

# Dashboard hierarchy: level -> (column used to filter, label column or None).
LEVEL_COLUMNS: dict[str, str] = {
    "vendor": COL_VENDOR,
    "mrp_controller": COL_MRP,
    "material": COL_MATERIAL,
}

# --------------------------------------------------------------------------- #
# Domain vocabulary (GIN material status logic, stakeholder presentation)
# --------------------------------------------------------------------------- #
STATUS_GOOD = "Good Part"
STATUS_BELOW_SAFETY = "Below Safety"
STATUS_POTENTIAL = "Potential Stock Out"
STATUS_ACTUAL = "Actual Stock Out"

# Ordered from least to most severe (used for charts and sorting).
STATUS_ORDER = [STATUS_GOOD, STATUS_BELOW_SAFETY, STATUS_POTENTIAL, STATUS_ACTUAL]
# Statuses that require attention. "Below Safety" is a warning, not critical.
CRITICAL_STATUSES = (STATUS_POTENTIAL, STATUS_ACTUAL)

IMPACT_NONE = "None"
IMPACT_LOGISTICS = "Logistics"
IMPACT_PRODUCTION = "Production"
IMPACT_MARKET = "Market"
IMPACT_ORDER = [IMPACT_NONE, IMPACT_LOGISTICS, IMPACT_PRODUCTION, IMPACT_MARKET]
# Stock-outs with these impacts are escalated to the Supply Risk Meeting.
ESCALATION_IMPACTS = (IMPACT_PRODUCTION, IMPACT_MARKET)

# Reference only (SAP status logic): above this share of safety buffer consumed,
# a delayed part is "Potential Stock Out" instead of "Below Safety".
SAFETY_BUFFER_THRESHOLD = 0.70

# Display colours, consistent across all dashboard pages.
STATUS_COLORS = {
    STATUS_GOOD: "#2ecc71",
    STATUS_BELOW_SAFETY: "#f1c40f",
    STATUS_POTENTIAL: "#e67e22",
    STATUS_ACTUAL: "#e74c3c",
}

# --------------------------------------------------------------------------- #
# Watchlist thresholds (each one is a documented, adjustable design choice)
# --------------------------------------------------------------------------- #
PERSISTENT_CRITICAL_SNAPSHOTS = 4   # consecutive critical snapshots up to the latest
RECURRENT_EPISODES = 3              # distinct critical episodes over the history
LONG_DELAY_DAYS = 14                # delivery delay considered long
MIN_POINTS_FOR_TREND = 4            # below this, no trend is claimed
TREND_REL_SLOPE = 0.05              # |slope| / mean above this => rising / falling
TOP_N = 5

# --------------------------------------------------------------------------- #
# Services (read from the environment, never hard-coded)
# --------------------------------------------------------------------------- #
LM_STUDIO_BASE_URL = os.environ.get("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
LM_STUDIO_MODEL = os.environ.get("LM_STUDIO_MODEL", "mistralai/mistral-7b-instruct-v0.3")
LM_STUDIO_TIMEOUT = 120.0


def get_deepl_key() -> str:
    """Return the DeepL API key from the environment (loads ``.env`` if available)."""
    try:  # optional dependency
        from dotenv import load_dotenv

        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:
        pass
    key = os.environ.get("DEEPL_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "DEEPL_API_KEY is not set. Copy .env.example to .env and fill it in."
        )
    return key
