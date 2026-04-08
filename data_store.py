"""
data_store.py
Saves exchange rate snapshots to a local SQLite database so the app
can draw trend charts without a paid history API endpoint.

On first run, 30 days of simulated history is generated automatically
so the charts work immediately.
"""


import random
import sqlite3
from datetime import date, timedelta
from typing import Dict, List, Optional

import pandas as pd

from config import cfg


class RateDataStore: 
    """
    SQLite-backed store for historical exchange rate snapshots.

    Table: rates(id, base, target, rate, recorded, synthetic)
    - recorded : 'YYYY-MM-DD' string
    - synthetic: 1 = simulated seed data, 0 = real API fetch
    """

    def __init__(self, db_path: str = cfg.db_path) -> None:
        self.db_path = db_path
        self._con = sqlite3.connect(db_path, check_same_thread=False)
        self._create_schema()

    def _create_schema(self) -> None:
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS rates (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                base      TEXT    NOT NULL,
                target    TEXT    NOT NULL,
                rate      REAL    NOT NULL,
                recorded  TEXT    NOT NULL,
                synthetic INTEGER NOT NULL DEFAULT 0
            )
        """)
        self._con.execute(
            "CREATE INDEX IF NOT EXISTS idx_btr "
            "ON rates (base, target, recorded)"
        )
        self._con.commit()

    def store_rates(
        self,
        base: str,
        rates: Dict[str, float],
        recorded_date: Optional[str] = None,
        synthetic: bool = False,
    ) -> None:
        """Save a batch of rates for one date into the database."""

        day  = recorded_date or str(date.today())
        flag = 1 if synthetic else 0
        rows = [(base, target, rate, day, flag) for target, rate in rates.items()]
        self._con.executemany(
            "INSERT INTO rates (base, target, rate, recorded, synthetic) "
            "VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        self._con.commit()

    def get_history(
        self,
        base: str,
        targets: List[str],
        days: int = 30,
    ) -> pd.DataFrame:
        """
        Return a DataFrame of daily rates for the last 'days' days.
        Index: DatetimeIndex. Columns: one per currency code.
        """
        since = str(date.today() - timedelta(days=days))
        ph    = ",".join("?" * len(targets))
        sql   = f"""
            SELECT recorded, target, rate
            FROM rates
            WHERE base = ? AND target IN ({ph}) AND recorded >= ?
            ORDER BY recorded
        """
        raw = pd.read_sql_query(sql, self._con, params=[base, *targets, since])
        if raw.empty:
            return pd.DataFrame()

        df = raw.pivot_table(
            index="recorded", columns="target", values="rate", aggfunc="last"
        )
        df.index = pd.to_datetime(df.index)
        df.sort_index(inplace=True)
        return df

    def has_data_for(self, base: str) -> bool:
        """Return True if the database has any rows for this base currency."""
        cur = self._con.execute(
            "SELECT 1 FROM rates WHERE base = ? LIMIT 1", (base,)
        )
        return cur.fetchone() is not None

    def seed_historical_data(
        self,
        base: str,
        current_rates: Dict[str, float],
        days: int = cfg.history_seed_days,
    ) -> None:
        """
        Generate 'days' of simulated history using a random walk.
        Rows are flagged synthetic=1 so the UI can show a notice.
        """
        today     = date.today()
        simulated = dict(current_rates)

        for delta in range(days, 0, -1):
            day_str  = str(today - timedelta(days=delta))
            snapshot = {}
            for code, current_rate in current_rates.items():
                prev      = simulated[code]
                shock     = random.gauss(0, 0.003)
                reversion = -0.02 * (prev - current_rate) / max(current_rate, 1e-9)
                simulated[code] = max(prev * (1 + shock + reversion), 1e-9)
                snapshot[code]  = round(simulated[code], 6)
            self.store_rates(base, snapshot, day_str, synthetic=True)

    def close(self) -> None:
        self._con.close()

    def __del__(self) -> None:
        try:
            self._con.close()
        except Exception:
            pass