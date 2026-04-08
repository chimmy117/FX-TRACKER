"""
chart_manager.py
Builds matplotlib charts for the Streamlit app.
Uses plain, simple colours — no config dependencies for styling.
"""


from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")   # must be before importing pyplot
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
import pandas as pd


# ── Simple colour palette ──────────────────────────────────────────────────

PALETTE = [
    "#4C72B0",  # blue
    "#55A868",  # green
    "#C44E52",  # red
    "#8172B2",  # purple
    "#CCB974",  # yellow
    "#64B5CD",  # light blue
    "#E07B54",  # orange
    "#76C7C0",  # teal
]

UP_COLOR   = "#55A868"   # green  — used for rising candles
DOWN_COLOR = "#C44E52"   # red    — used for falling candles


def _style_axes(fig: Figure, ax:plt.Axes) -> None:
    """Apply a clean, minimal style to any figure/axes pair."""
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#F8F9FA")
    ax.tick_params(colors="#444444", labelsize=9)
    ax.xaxis.label.set_color("#444444")
    ax.yaxis.label.set_color("#444444")
    ax.title.set_color("#222222")
    for spine in ax.spines.values():
        spine.set_edgecolor("#DDDDDD")
    ax.grid(True, color="#EEEEEE", linewidth=0.8, linestyle="--")




class ChartManager:
    """
    Factory for all matplotlib figures used in the FX Tracker.
    All methods are static — this class holds no state.
    """

    @staticmethod
    def build_trend_chart(
        history_df: pd.DataFrame,
        base: str,
        figsize: tuple = (10, 4),
    ) -> Optional[Figure]:
        """
        Line chart showing exchange rate movement over time.
        One line per currency. Legend shows % change over the period.
        """
        if history_df is None or history_df.empty:
            return None

        fig, ax = plt.subplots(figsize=figsize, tight_layout=True)
        _style_axes(fig, ax)

        for idx, col in enumerate(history_df.columns):
            series = history_df[col].dropna()
            if series.empty:
                continue

            color = PALETTE[idx % len(PALETTE)]
            pct   = ((series.iloc[-1] / series.iloc[0]) - 1) * 100
            arrow = "▲" if pct >= 0 else "▼"
            label = f"{col}  {arrow} {abs(pct):.2f}%"

            ax.plot(series.index, series.values,
                    color=color, linewidth=2, label=label)
            # Highlight the last point
            ax.plot(series.index[-1], series.iloc[-1],
                    "o", color=color, markersize=5)

        ax.set_title(f"Exchange Rate Trend  —  Base: {base}",
                     fontsize=12, fontweight="bold", pad=10)
        ax.set_xlabel("Date", labelpad=6)
        ax.set_ylabel(f"Units per 1 {base}", labelpad=6)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=8)
        ax.legend(loc="upper left", fontsize=8, framealpha=0.5)

        return fig

    @staticmethod
    def build_bar_chart(
        rates: Dict[str, float],
        base: str,
        currencies: List[str],
        figsize: tuple = (10, 4),
    ) -> Optional[Figure]:
        """
        Horizontal bar chart of current spot rates.
        Bars are sorted by rate value (lowest at top).
        """
        items = sorted(
            [(k, v) for k, v in rates.items() if k in currencies],
            key=lambda x: x[1],
        )
        if not items:
            return None

        codes  = [k for k, _ in items]
        values = [v for _, v in items]
        colors = [PALETTE[i % len(PALETTE)] for i in range(len(items))]

        fig, ax = plt.subplots(figsize=figsize, tight_layout=True)
        _style_axes(fig, ax)

        bars = ax.barh(codes, values, color=colors, edgecolor="#FFFFFF", linewidth=0.5)

        # Value label next to each bar
        for bar, val in zip(bars, values):
            label = f"{val:,.4f}" if val < 10_000 else f"{val:,.0f}"
            ax.text(
                bar.get_width() * 1.005,
                bar.get_y() + bar.get_height() / 2,
                label, va="center", ha="left",
                color="#555555", fontsize=8,
            )

        ax.set_title(f"Spot Rates  —  1 {base} equals ...",
                     fontsize=12, fontweight="bold", pad=10)
        ax.set_xlabel("Exchange Rate", labelpad=6)
        ax.set_xlim(right=max(values) * 1.18)   # space for labels
        ax.tick_params(axis="y", labelsize=10)

        return fig

    @staticmethod
    def build_volatility_chart(
        history_df: pd.DataFrame,
        base: str,
        figsize: tuple = (10, 3.5),
    ) -> Optional[Figure]:
        """
        Bar chart of annualised volatility for each currency.
        Volatility = std(daily % returns) x sqrt(252) x 100
        """
        if history_df is None or history_df.empty or len(history_df) < 3:
            return None

        log_ret = history_df.pct_change().dropna()
        vol     = (log_ret.std() * (252 ** 0.5) * 100).sort_values(ascending=False)

        if vol.empty:
            return None

        fig, ax = plt.subplots(figsize=figsize, tight_layout=True)
        _style_axes(fig, ax)

        colors = [PALETTE[i % len(PALETTE)] for i in range(len(vol))]
        ax.bar(vol.index, vol.values, color=colors,
               edgecolor="#FFFFFF", linewidth=0.5)

        for i, (code, v) in enumerate(vol.items()):
            ax.text(i, v + 0.15, f"{v:.1f}%",
                    ha="center", va="bottom", color="#555555", fontsize=8)

        ax.set_title(f"Annualised Volatility  —  Base: {base}",
                     fontsize=12, fontweight="bold", pad=10)
        ax.set_ylabel("Volatility (%)", labelpad=6)
        ax.tick_params(axis="x", labelsize=10)

        return fig

    @staticmethod
    def build_candlestick_chart(
        history_df: pd.DataFrame,
        base: str,
        target: str,
        figsize: tuple = (10, 4),
    ) -> Optional[Figure]:
        """
        Weekly OHLC candlestick chart for a single currency pair.
        Green candles = price rose that week. Red = price fell.
        """
        if history_df is None or history_df.empty or target not in history_df.columns:
            return None

        series = history_df[target].dropna()
        if len(series) < 10:
            return None

        ohlc = series.resample("W-FRI").agg(
            open="first", high="max", low="min", close="last"
        ).dropna()

        if len(ohlc) < 2:
            return None

        fig, ax = plt.subplots(figsize=figsize, tight_layout=True)
        _style_axes(fig, ax)

        body_w = 4      # candle body width
        wick_w = 0.8    # wick width

        up   = ohlc[ohlc.close >= ohlc.open]
        down = ohlc[ohlc.close  < ohlc.open]

        # Bodies
        ax.bar(up.index,   up.close   - up.open,   body_w,
               bottom=up.open,   color=UP_COLOR,   alpha=0.85)
        ax.bar(down.index, down.close - down.open, body_w,
               bottom=down.open, color=DOWN_COLOR, alpha=0.85)

        # Upper wicks
        ax.bar(up.index,   up.high   - up.close,   wick_w,
               bottom=up.close,   color=UP_COLOR,   alpha=0.6)
        ax.bar(down.index, down.high - down.close, wick_w,
               bottom=down.close, color=DOWN_COLOR, alpha=0.6)

        # Lower wicks
        ax.bar(up.index,   up.open   - up.low,     wick_w,
               bottom=up.low,   color=UP_COLOR,   alpha=0.6)
        ax.bar(down.index, down.open - down.low,   wick_w,
               bottom=down.low, color=DOWN_COLOR, alpha=0.6)

        ax.set_title(f"{base} / {target}  —  Weekly OHLC",
                     fontsize=12, fontweight="bold", pad=10)
        ax.set_ylabel(f"{target} per 1 {base}", labelpad=6)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=8)

        return fig