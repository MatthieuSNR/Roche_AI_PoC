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


# ======================================================================================
# Pseudonymisation of the PROMPT sent to a cloud LLM (Mistral API)
# ======================================================================================
# The prompt only contains aggregated statistics (shares, counts, trends: no price, no
# volume) and a few planner comments. Even so, identifying elements are replaced by
# aliases before the request leaves the machine, as an additional safeguard:
#
# * supplier names (statistics and comments)   -> VENDOR_n
# * MRP controllers (statistics)               -> MRP_n
# * purchasing groups (statistics)             -> PGROUP_n
# * material numbers                           -> MATERIAL_n
# * e-mails, @-mentions, long numbers, "Roche" in the comments -> EMAIL_n, PERSON_n, ID_n, COMPANY_n
#
# The alias -> original table stays in memory on this machine; the aliases that the model
# writes in its answer are replaced by the original values before display (restore_text).
# Limits (thesis 3.8): same as for DeepL (names in abbreviated or misspelled form, persons
# without "@"). MRP controllers and purchasing groups are short codes: they are replaced
# in the statistics (exact values) but not searched inside the free-text comments.

ALIAS_LABELS = ("VENDOR", "MRP", "PGROUP", "MATERIAL", "EMAIL", "PERSON", "ID", "COMPANY")
ALIAS = re.compile(r"(?<![A-Za-z0-9_])((?:" + "|".join(ALIAS_LABELS) + r")_\d+)(?!\d)")
NOT_AN_ENTITY = {"Unknown", "Unknown vendor", "None", ""}


def _vendor_key(name: str) -> str:
    """Normalised supplier name: 'ACME Medical GmbH' and 'Acme Medical' share one alias."""
    short = re.sub(r"\s+", " ", name).strip()
    while LEGAL_SUFFIX.search(short):
        short = LEGAL_SUFFIX.sub("", short).strip()
    return short.lower()


class PromptPseudonymiser:
    """Reversible aliases for one request to a cloud LLM.

    >>> p = PromptPseudonymiser(df)            # df: the loaded comments table
    >>> safe_stats = p.apply(stats)            # same structure, aliases instead of names
    >>> p.restore_text(answer)                 # aliases -> original names
    """

    def __init__(self, df: pd.DataFrame):
        self.reverse: dict[str, str] = {}       # alias -> original value
        self._forward: dict[tuple, str] = {}    # (label, key) -> alias
        self._counters: dict[str, int] = {}
        self._exact: dict[str, str] = {}        # exact value -> label (statistics keys and values)

        vendors = df["VENDOR_NAME"].dropna().astype(str).unique() if "VENDOR_NAME" in df else []
        for label, column in (("MRP", "MRP_CONTROLLER"), ("PGROUP", "PURCHASING_GROUP"),
                              ("MATERIAL", "MATERIAL_NUMBER")):
            if column in df:
                for v in df[column].dropna().astype(str).unique():
                    if v.strip() not in NOT_AN_ENTITY:
                        self._exact[v.strip()] = label
        for v in vendors:
            if v.strip() not in NOT_AN_ENTITY:
                self._exact[v.strip()] = "VENDOR"

        materials = df["MATERIAL_NUMBER"].dropna().astype(str).tolist() if "MATERIAL_NUMBER" in df else []
        self._patterns = build_patterns(vendor_names(pd.Series(list(vendors), dtype=str)), materials)

    def fresh(self) -> "PromptPseudonymiser":
        """New pseudonymiser for one request: same entity lists (expensive to build), empty aliases."""
        other = object.__new__(PromptPseudonymiser)
        other.reverse, other._forward, other._counters = {}, {}, {}
        other._exact, other._patterns = self._exact, self._patterns
        return other

    def _alias(self, label: str, original: str, key: str | None = None) -> str:
        key = (label, key if key is not None else original)
        if key not in self._forward:
            self._counters[label] = self._counters.get(label, 0) + 1
            alias = f"{label}_{self._counters[label]}"
            self._forward[key] = alias
            self.reverse[alias] = original
        return self._forward[key]

    def _text(self, text: str) -> str:
        stripped = text.strip()
        if stripped in self._exact:  # statistics keys/values: whole string is an entity
            label = self._exact[stripped]
            return self._alias(label, stripped, _vendor_key(stripped) if label == "VENDOR" else None)
        for label, pattern in self._patterns:  # free text (comments)
            def sub(match, label=label):
                value = match.group(0)
                return self._alias(label, value, _vendor_key(value) if label == "VENDOR" else None)
            text = pattern.sub(sub, text)
        return text

    def apply(self, obj):
        """Return a copy of obj (dict / list / str) with every identifying string aliased."""
        if isinstance(obj, dict):
            return {(self._text(k) if isinstance(k, str) else k): self.apply(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self.apply(v) for v in obj]
        if isinstance(obj, str):
            return self._text(obj)
        return obj

    def restore_text(self, text: str) -> str:
        """Replace the aliases written by the model by the original values."""
        return ALIAS.sub(lambda m: self.reverse.get(m.group(1), m.group(1)), text)

    def stream_restored(self, pieces):
        """Restore aliases in a stream of text pieces. The last (possibly unfinished) word is
        held back until its end is known, so that 'VENDOR_1' is never shown as half an alias."""
        buffer = ""
        for piece in pieces:
            buffer += piece
            cut = max(buffer.rfind(" "), buffer.rfind("\n")) + 1
            if cut:
                yield self.restore_text(buffer[:cut])
                buffer = buffer[cut:]
        if buffer:
            yield self.restore_text(buffer)
