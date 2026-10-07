"""Roche AI PoC: statistics-first analytics for the Material Availability Dashboard.

Layers (each one only depends on the layers above it):
    config  ->  data  ->  stats  ->  nlp  ->  llm / ml
The Streamlit dashboard (``dashboard/``) is a thin consumer of this package.
"""

__version__ = "0.2.0"
