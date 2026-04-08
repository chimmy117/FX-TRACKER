"""
currency_converter.py
Pure conversion arithmetic. No API calls, no database, no GUI.
All rates are relative to a single base currency.
Cross-rates are calculated by pivoting through that base.
"""



from typing import Dict, List, Optional, Tuple


class CurrencyConverter:
    """
    Converts monetary amounts between any pair of loaded currencies.
    """

    def __init__(self, rates: Dict[str, float], base_currency: str) -> None:
        self._rates: Dict[str, float] = dict(rates)
        self.base: str = base_currency
        self._rates[base_currency] = 1.0    # base always equals 1

    def get_rate(self, from_curr: str, to_curr: str) -> float:
        """Return how many units of to_curr equal 1 unit of from_curr."""
        if from_curr == to_curr:
            return 1.0
        self._require(from_curr, to_curr)
        from_rate = self._rates[from_curr]
        if from_rate == 0:
            raise ZeroDivisionError(f"Rate for {from_curr} is 0 — data may be corrupt.")
        return self._rates[to_curr] / from_rate

    def convert(
        self,
        amount: float,
        from_curr: str,
        to_curr: str,
    ) -> Tuple[float, float]:
        """
        Convert amount from from_curr to to_curr.
        Returns (converted_amount, rate_used).
        """
        rate = self.get_rate(from_curr, to_curr)
        return amount * rate, rate

    def convert_to_many(
        self,
        amount: float,
        from_curr: str,
        targets: List[str],
    ) -> Dict[str, Dict[str, float]]:
        """
        Convert amount into every currency in targets.
    
        """
        results: Dict[str, Dict[str, float]] = {}
        for target in targets:
            if target == from_curr:
                continue
            try:
                converted, rate = self.convert(amount, from_curr, target)
                results[target] = {"converted": converted, "rate": rate}
            except (ValueError, ZeroDivisionError):
                pass
        return results

    def get_rate_matrix(
        self,
        codes: List[str],
    ) -> Dict[str, Dict[str, Optional[float]]]:
        """Build an N x N cross-rate table for the given currency codes."""
        matrix: Dict[str, Dict[str, Optional[float]]] = {}
        for src in codes:
            matrix[src] = {}
            for dst in codes:
                try:
                    matrix[src][dst] = round(self.get_rate(src, dst), 6)
                except (ValueError, ZeroDivisionError):
                    matrix[src][dst] = None
        return matrix

    @property
    def available_currencies(self) -> List[str]:
        """Alphabetically sorted list of loaded currency codes."""
        return sorted(self._rates.keys())

    def has(self, code: str) -> bool:
        """Return True if code is in the loaded rate table."""
        return code in self._rates

    def _require(self, *codes: str) -> None:
        missing = [c for c in codes if c not in self._rates]
        if missing:
            raise ValueError(
                f"Currency code(s) not found in loaded rates: {', '.join(missing)}"
            )