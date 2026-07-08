"""Lightweight airport/city lookup helpers.

Manual entry is always allowed. This module only provides best-effort
suggestions (city name -> IATA code) and normalization; it never blocks
user input.
"""

# Small built-in reference table. Not exhaustive -- manual override always wins.
KNOWN_AIRPORTS = {
    "KOCHI": "COK",
    "COCHIN": "COK",
    "TRIVANDRUM": "TRV",
    "THIRUVANANTHAPURAM": "TRV",
    "DUBAI": "DXB",
    "ABU DHABI": "AUH",
    "SHARJAH": "SHJ",
    "JEDDAH": "JED",
    "MEDINA": "MED",
    "MADINAH": "MED",
    "RIYADH": "RUH",
    "BANGKOK": "BKK",
    "PHUKET": "HKT",
    "SINGAPORE": "SIN",
    "KUALA LUMPUR": "KUL",
    "DOHA": "DOH",
    "MUSCAT": "MCT",
    "KUWAIT": "KWI",
    "BAHRAIN": "BAH",
    "CHENNAI": "MAA",
    "MUMBAI": "BOM",
    "DELHI": "DEL",
    "CALICUT": "CCJ",
    "KOZHIKODE": "CCJ",
    "MOSCOW": "MOW",
    "ISTANBUL": "IST",
    "LONDON": "LON",
    "PARIS": "PAR",
    "NEW YORK": "NYC",
    "MALE": "MLE",
    "COLOMBO": "CMB",
    "CAIRO": "CAI",
    "MANILA": "MNL",
    "HONG KONG": "HKG",
    "TOKYO": "TYO",
    "SEOUL": "SEL",
}


def normalize_airport_input(value: str) -> str:
    """Return an IATA-like code for a free-text city/airport entry.

    If the text already looks like a 3-letter code, upper-case and return it.
    Otherwise try a lookup; if no match, return the trimmed upper-cased input
    unchanged so manual entry always works.
    """
    if not value:
        return ""
    text = value.strip()
    if len(text) == 3 and text.isalpha():
        return text.upper()
    match = KNOWN_AIRPORTS.get(text.upper())
    if match:
        return match
    return text.upper()


def suggest_airport_code(value: str):
    """Return a suggested code, or None if no confident match found."""
    if not value:
        return None
    text = value.strip().upper()
    if len(text) == 3 and text.isalpha():
        return text
    return KNOWN_AIRPORTS.get(text)
