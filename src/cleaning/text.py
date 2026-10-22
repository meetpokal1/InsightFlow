"""Small text-cleaning helpers. Each one takes a Series and returns a Series."""

from src.cleaning.rules import CITY_ALIASES

# strings that really mean "no value"
NULL_TOKENS = {"", "nan", "none", "null", "n/a", "na", "-", "--"}


def clean_text(series, case=None):
    """Trim, collapse repeated spaces and turn null-like strings into missing values.

    case can be "title", "upper" or "lower"; None keeps the original case.
    """
    text = series.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    text = text.mask(text.str.lower().isin(NULL_TOKENS))
    if case == "title":
        text = text.str.title()
    elif case == "upper":
        text = text.str.upper()
    elif case == "lower":
        text = text.str.lower()
    return text


def normalize_id(series):
    """' p0012 ' -> 'P0012'"""
    return clean_text(series).str.replace(" ", "", regex=False).str.upper()


def tidy_name(series):
    """Fix names written all in upper or all in lower case and leave mixed case alone.

    'PRIYA PATEL' -> 'Priya Patel', but 'Crest Consulting LLP' stays as it is.
    """
    text = clean_text(series)
    one_case = (text == text.str.upper()) | (text == text.str.lower())
    one_case = one_case.fillna(False).astype(bool)
    return text.where(~one_case, text.str.title()).str.replace(r"\bLlp\b", "LLP", regex=True)


def clean_phone(series):
    """Keep the last 10 digits of a phone number: '+91 98765 43210' -> '9876543210'.

    Numbers with fewer than 10 digits are treated as missing.
    """
    digits = series.astype("string").str.replace(r"\D", "", regex=True)
    return digits.str[-10:].where(digits.str.len() >= 10)


def map_vocabulary(series, mapping):
    """Map free text onto a fixed list of values, ignoring case and extra spaces.

    Values that are not in the mapping come back as missing, so the caller can decide
    whether to use a default or reject the row.
    """
    key = clean_text(series).str.lower()
    return key.map(mapping).astype("string")


def standardize_city(series):
    """'bangalore ' -> 'Bengaluru', 'MUMBAI' -> 'Mumbai'. Unknown cities are title-cased."""
    text = clean_text(series)
    aliased = text.str.lower().map(CITY_ALIASES).astype("string")
    return aliased.fillna(text.str.title())


def standardize_location_name(series):
    """'Bangalore Warehouse' -> 'Bengaluru Warehouse'"""
    text = clean_text(series).str.title()
    for old, new in CITY_ALIASES.items():
        text = text.str.replace(rf"(?i)\b{old}\b", new, regex=True)
    return text


def remap_ids(series, id_map):
    """Replace ids using a dict, e.g. duplicate customer id -> the customer we keep."""
    if not id_map:
        return series
    return series.map(id_map).astype("string").fillna(series)
