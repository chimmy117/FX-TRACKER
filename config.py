"""
config.py

Central settings and currency catalogue for the FX Tracker.
Every other file imports 'cfg' from here.

"""


from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True) # @dataclass makes it easy to define a class with attributes, and frozen=True makes it immutable
class Config: 

    # API settings 
    api_base_url: str = "https://v6.exchangerate-api.com/v6"
    api_key_env_var: str = "EXCHANGE_RATE_API_KEY"
    cache_ttl_seconds: int = 300        # time to load cache (5 minutes)

    #  Database 
    db_path: str = "exchange_rates.db"
    history_seed_days: int = 30

    #  Default UI values 
    default_base: str = "NGN"
    default_watchlist: List[str] = field(default_factory=lambda: [
        "USD", "EUR", "GBP", "JPY", "ZAR", "CHF", "CNY", "GHS"
    ])


# Currency catalogue 

CURRENCY_NAMES: Dict[str, str] = {
    # Africa Currencies (na us dey here)
    "NGN": "Nigerian Naira",
    "GHS": "Ghanaian Cedi",
    "KES": "Kenyan Shilling",
    "EGP": "Egyptian Pound",
    "ZAR": "South African Rand",
    "ZMW": "Zambian Kwacha",
    "TZS": "Tanzanian Shilling",
    "UGX": "Ugandan Shilling",
    "XOF": "West African CFA Franc",
    "XAF": "Central African CFA Franc",
    "MAD": "Moroccan Dirham",
    "LRD": "Liberian Dollar",

    # Major world currencies (in case we want japa)
    "USD": "United States Dollar",
    "EUR": "Euro",
    "GBP": "British Pound Sterling",
    "JPY": "Japanese Yen",
    "AUD": "Australian Dollar",
    "CAD": "Canadian Dollar",
    "CHF": "Swiss Franc",
    "CNY": "Chinese Yuan",
    "SEK": "Swedish Krona",
    "BRL": "Brazilian Real",
    "INR": "Indian Rupee",
    "AED": "UAE Dirham",
    "SAR": "Saudi Riyal",
    "SGD": "Singapore Dollar",
    "HUF": "Hungarian Forint",
    "IDR": "Indonesian Rupiah",
    "ILS": "Israeli New Shekel",
    "NZD": "New Zealand Dollar",
    "PHP": "Philippine Peso",
    "PKR": "Pakistani Rupee",
    "PLN": "Polish Zloty",
    "RON": "Romanian Leu",
    "THB": "Thai Baht",
    "TRY": "Turkish Lira",
    "TWD": "Taiwan New Dollar",
    "UAH": "Ukrainian Hryvnia",
    "VND": "Vietnamese Dong",
}

# Sorted list used to populate all dropdowns
ALL_CURRENCY_CODES: List[str] = sorted(CURRENCY_NAMES.keys())

# Module-level singleton imported by every other file
cfg = Config()