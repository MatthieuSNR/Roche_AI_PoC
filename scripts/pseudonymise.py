"""
Pseudonymisation of planner comments before they are sent to an external service (DeepL).

Identifying elements are replaced by numbered placeholders, e.g.
    "Lieferant Acme GmbH, PO 4500123456, Rückfrage an max.muster@roche.com"
 -> "Lieferant VENDOR_1, PO ID_1, Rückfrage an EMAIL_1"
The mapping placeholder -> original value stays on this machine and is used to put the
original values back into the English translation (restore). DeepL therefore never sees:

* e-mail addresses                                    -> EMAIL_n
* @-mentions of colleagues ("@Muster:")               -> PERSON_n
* supplier names known from the VENDOR_NAME column    -> VENDOR_n
* material numbers known from MATERIAL_NUMBER         -> MATERIAL_n
* any other number with 6 digits or more (PO, batch),
  also when glued to letters ("PO4500123456")         -> ID_n
* words containing the company name ("Roche")         -> COMPANY_n

Placeholders are wrapped in <keep>…</keep> tags and sent with tag_handling="xml" and
ignore_tags=["keep"], so DeepL copies them unchanged into the translation.

Limits (to be stated in the thesis, 3.8): supplier names written in an abbreviated or
misspelled form, and names of persons written without "@" or e-mail address, are not detected.
"""

import html
import re

import pandas as pd

# Legal suffixes removed to build the short form of a supplier name ("Acme GmbH" -> "Acme")
LEGAL_SUFFIX = re.compile(
    r"[\s,.]+(gmbh(\s*&\s*co\.?\s*kg)?|ag|kg|sa|sas|srl|s\.r\.l\.|bv|b\.v\.|nv|inc\.?|ltd\.?|llc|"
    r"limited|corp\.?|corporation|co\.?|plc|oy|ab|as|spa|s\.p\.a\.)$",
    re.IGNORECASE,
)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
MENTION = re.compile(r"@[A-Za-zÄÖÜäöüß][\w.-]*[\w]")
LONG_NUMBER = re.compile(r"\d{6,}")
COMPANY = re.compile(r"\w*roche\w*", re.IGNORECASE)
MIN_NAME_LENGTH = 4  # shorter names ("ABC") would match ordinary words too often
TAG = re.compile(r"<keep>([A-Z]+_\d+)</keep>")


def vendor_names(series: pd.Series) -> list[str]:
    """Full and short forms of every supplier name, longest first (so the full name wins)."""
    names = set()
    for raw in series.dropna().astype(str):
        name = re.sub(r"\s+", " ", raw).strip()
        short = name
        while LEGAL_SUFFIX.search(short):
            short = LEGAL_SUFFIX.sub("", short).strip()
        for n in (name, short):
            if len(n) >= MIN_NAME_LENGTH and not n.isdigit():
                names.add(n)
    return sorted(names, key=len, reverse=True)


def build_patterns(vendors: list[str], materials: list[str]) -> list[tuple[str, re.Pattern]]:
    """Ordered (label, regex) list. Order matters: e-mails before numbers, names before IDs."""
    patterns = [("EMAIL", EMAIL), ("PERSON", MENTION)]
    if vendors:
        patterns.append(("VENDOR", re.compile(
            r"(?<!\w)(" + "|".join(map(re.escape, vendors)) + r")(?!\w)", re.IGNORECASE)))
    materials = sorted({str(m).strip() for m in materials if len(str(m).strip()) >= 5}, key=len, reverse=True)
    if materials:
        patterns.append(("MATERIAL", re.compile(r"(?<![\w])(" + "|".join(map(re.escape, materials)) + r")(?![\w])")))
    patterns += [("ID", LONG_NUMBER), ("COMPANY", COMPANY)]
    return patterns


def pseudonymise(text: str, patterns) -> tuple[str, dict]:
    """Return (xml-safe text with <keep> placeholders, {placeholder: original})."""
    mapping, counters = {}, {}
    seen = {}  # same value twice in a comment -> same placeholder

    def replacer(label):
        def _sub(match):
            value = match.group(0)
            key = (label, value)
            if key not in seen:
                counters[label] = counters.get(label, 0) + 1
                seen[key] = f"{label}_{counters[label]}"
                mapping[seen[key]] = value
            return "\x00" + seen[key] + "\x01"  # temporary markers, escaped text stays clean
        return _sub

    for label, pattern in patterns:
        text = pattern.sub(replacer(label), text)
    text = html.escape(text, quote=False)  # needed because DeepL parses the text as XML
    text = text.replace("\x00", "<keep>").replace("\x01", "</keep>")
    return text, mapping


def restore(translated: str, mapping: dict) -> str:
    """Put the original values back into the translation and undo the XML escaping."""
    text = TAG.sub(lambda m: mapping.get(m.group(1), m.group(1)), translated)
    return html.unescape(text)


def report(texts: list[str], patterns) -> pd.Series:
    """Number of texts in which each kind of element was replaced (for --dry-run and the thesis)."""
    counts = {}
    for t in texts:
        for label in {k.split("_")[0] for k in pseudonymise(t, patterns)[1]}:
            counts[label] = counts.get(label, 0) + 1
    return pd.Series(counts, dtype=int).sort_values(ascending=False)
