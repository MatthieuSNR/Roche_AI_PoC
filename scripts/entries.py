"""
Format of a comment cell that holds several journal entries.

The entries of one cell are written one after the other, separated by ENTRY_SEPARATOR (" ¦▸ "):
  "Vorzug angefragt ¦▸ Lieferant bestätigt ¦▸ Wareneingang KW34"
The marker is visible in Excel, in a text editor, in grep and in the dashboard, and it appears nowhere in
the raw comments (checked on the 26 snapshots), so a cell can always be cut back into its entries.
Every module (data_cleaning, abbreviations, translation, stats_engine, app) uses these two functions.
"""

ENTRY_SEPARATOR = " ¦▸ "


def join_entries(entries):
    return ENTRY_SEPARATOR.join(entries)


def split_cell(text):
    """Entries of a cell, in the order they were written (positions match Entry_Languages)."""
    return [e.strip() for e in str(text).split(ENTRY_SEPARATOR.strip())]
