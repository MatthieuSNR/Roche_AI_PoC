# config.py
# API keys are read from the .env file at the project root (never pushed to GitHub, see .gitignore).
# Copy .env.example to .env and fill DEEPL_API_KEY.

import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")
