"""
api_client.py

Fetches live exchange rates from ExchangeRate-API v6.
API key is in .env file.

"""



import os
import time
from typing import Dict

import requests
from dotenv import load_dotenv

from config import cfg

load_dotenv()  # reads .env from the project folder


class ExchangeRateClient:
    """
    Wrapper around the ExchangeRate-API v6 REST endpoint.
    Caches responses in memory to avoid burning the free quota.
    """

    def __init__(self) -> None:
        self.key: str = self._load_key()
        self._cache: Dict[str, Dict] = {}
        """ 
        this function is used to store the cached exchange rates for different base currencies.
        """

    def get_latest_rates(self, base: str = "NGN") -> Dict:

        """
        Return the latest exchange rates for a given base currency.
        Result is cached for cfg.cache_ttl_seconds (5 minutes).
        """
        cached = self._cache.get(base)
        if cached:
            age = time.time() - cached["fetched_at"]
            if age < cfg.cache_ttl_seconds:
                return cached["data"]

        url = f"{cfg.api_base_url}/{self.key}/latest/{base}"
        data = self._get(url)
        self._cache[base] = {"data": data, "fetched_at": time.time()}
        return data

    def clear_cache(self) -> None:
        """Force the next call to hit the network."""
        self._cache.clear()

    @property # @property decorator allows us to access the method as an attribute, so we can do client.has_valid_key instead of client.has_valid_key() 
    def has_valid_key(self) -> bool:
        return bool(self.key)

    @staticmethod # @staticmethod decorator indicates that this method does not depend on the instance (self) and can be called on the class itself, e.g. ExchangeRateClient._load_key()
    def _load_key() -> str:
        key = os.getenv("EXCHANGE_RATE_API_KEY", "").strip()
        if not key:
            raise EnvironmentError(
                "EXCHANGE_RATE_API_KEY is not set.\n\n"
                "Steps to fix:\n"
                "  1. Register for FREE at https://app.exchangerate-api.com/sign-up\n"
                "  2. Create a .env file in the project folder:\n"
                "         EXCHANGE_RATE_API_KEY=your_key_here\n"
                "  3. Restart the application."
            )
        return key

    @staticmethod
    def _get(url: str) -> Dict:
        try:
            response = requests.get(url, timeout=12)
            response.raise_for_status()
            body = response.json()
        except requests.exceptions.ConnectionError:
            raise ConnectionError(
                "Cannot reach exchangerate-api.com. "
                "Please check your internet connection."
            )
        except requests.exceptions.Timeout:
            raise TimeoutError("ExchangeRate-API did not respond within 12 seconds.")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(
                f"HTTP {e.response.status_code}: {e.response.text[:300]}"
            )
        return body