# config.py
# API keys are read from the .env file at the project root (never pushed to GitHub, see .gitignore).
# Copy .env.example to .env and fill DEEPL_API_KEY.

import os

from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
_PASSWORD_FROM_SHELL = "APP_PASSWORD" in os.environ   # e.g. APP_PASSWORD= for a local test without password
load_dotenv(ENV_PATH)

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")


def app_password():
    """Password of the dashboard: the one given when starting it (APP_PASSWORD=... streamlit run), otherwise the
    one in .env, read again at every call so that a change applies without restarting the dashboard."""
    if _PASSWORD_FROM_SHELL or not os.path.exists(ENV_PATH):
        return os.getenv("APP_PASSWORD", "")
    from dotenv import dotenv_values
    return dotenv_values(ENV_PATH).get("APP_PASSWORD") or ""
