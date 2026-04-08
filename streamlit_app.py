"""
streamlit_app.py

Streamlit web app for the FX Tracker.

Run with:
    streamlit run streamlit_app.py

A browser tab will open at http://localhost:8501
"""



import streamlit as st
import pandas as pd
from typing import Dict, List

from config import cfg, CURRENCY_NAMES, ALL_CURRENCY_CODES
from api_client import ExchangeRateClient
from data_store import RateDataStore
from currency_converter import CurrencyConverter
from chart_manager import ChartManager


# Must be the very first Streamlit call
st.set_page_config(
    page_title="FX Tracker",
    page_icon="💱",
    layout="wide",
)


class StreamlitFXApp:
    """
    Main Streamlit application class.

    Three tabs:
      1. Dashboard  - live rate cards and bar chart
      2. Converter  - single and multi-currency conversion
      3. Trends     - historical line, volatility, and candlestick charts
    """

    _PERIODS: Dict[str, int] = {
        "7 Days":  7,
        "14 Days": 14,
        "30 Days": 30,
        "60 Days": 60,
        "90 Days": 90,
    }

    def __init__(self) -> None: 
        self._init_services()
        self._init_state()

    def _init_services(self) -> None:
        @st.cache_resource
        def _client():
            return ExchangeRateClient()

        @st.cache_resource
        def _store():
            return RateDataStore()

        @st.cache_resource
        def _charts():
            return ChartManager()

        self.client = _client()
        self.store  = _store()
        self.charts = _charts()

    def _init_state(self) -> None:
        st.session_state.setdefault("base",      cfg.default_base)
        st.session_state.setdefault("watchlist", list(cfg.default_watchlist))
        st.session_state.setdefault("conv_from", cfg.default_base)
        st.session_state.setdefault("conv_to",   "USD")

    @st.cache_data(ttl=cfg.cache_ttl_seconds)
    def _fetch_rates(_self, base: str) -> Dict:
        return _self.client.get_latest_rates(base)

    def _sidebar(self) -> tuple[str, List[str]]:
        with st.sidebar:
            st.title("FX Tracker")
            st.caption("Live exchange rates")
            st.divider()

            base_idx = ALL_CURRENCY_CODES.index(st.session_state.base) \
                if st.session_state.base in ALL_CURRENCY_CODES else 0
            base = st.selectbox("Base Currency", ALL_CURRENCY_CODES, index=base_idx)

            if base != st.session_state.base:
                st.session_state.base = base
                self.client.clear_cache()
                st.rerun()

            st.divider()

            watchlist = st.multiselect(
                "Watchlist",
                [c for c in ALL_CURRENCY_CODES if c != base],
                default=[c for c in st.session_state.watchlist if c != base],
            )
            if watchlist:
                st.session_state.watchlist = watchlist

            st.divider()

            if st.button("Refresh Rates", use_container_width=True):
                self.client.clear_cache()
                st.cache_data.clear()
                st.rerun()

            st.caption("Powered by ExchangeRate-API")

        return base, watchlist or st.session_state.watchlist

    def _tab_dashboard(self, rates_data: Dict, watchlist: List[str], base: str) -> None:
        rates   = rates_data.get("conversion_rates", {})
        tracked = [c for c in watchlist if c in rates]
        updated = rates_data.get("time_last_update_utc", "—")

        c1, c2, c3 = st.columns(3)
        c1.metric("Base Currency",      base)
        c2.metric("Last Updated",       updated[:10])
        c3.metric("Currencies Tracked", len(tracked))

        st.divider()
        st.subheader("Live Rates")

        if not tracked:
            st.info("Add currencies to your watchlist in the sidebar.")
        else:
            cols_per_row = 4
            for i in range(0, len(tracked), cols_per_row):
                chunk = tracked[i:i + cols_per_row]
                cols  = st.columns(cols_per_row)
                for j, code in enumerate(chunk):
                    rate    = rates[code]
                    name    = CURRENCY_NAMES.get(code, code)
                    display = f"{rate:,.4f}" if rate < 10_000 else f"{rate:,.0f}"
                    with cols[j]:
                        st.metric(label=f"{base} to {code}", value=display, help=name)

        st.divider()
        st.subheader("Rate Comparison")
        fig = self.charts.build_bar_chart(rates, base, tracked)
        if fig:
            st.pyplot(fig, use_container_width=True)
        else:
            st.info("Add currencies to your watchlist to see this chart.")

        st.divider()
        st.subheader("All Available Rates")
        rows = [
            {
                "Code":     code,
                "Currency": CURRENCY_NAMES.get(code, "—"),
                f"Rate (1 {base})":    round(rate, 6),
                f"Inverse (1/{base})": round(1 / rate, 6) if rate else "—",
            }
            for code, rate in sorted(rates.items())
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=350)

    def _tab_converter(self, converter: CurrencyConverter) -> None:
        avail = converter.available_currencies
        st.subheader("Convert")

        c1, c2, c3 = st.columns(3)
        with c1:
            amount = st.number_input("Amount", min_value=0.0, value=100.0, step=10.0, format="%.2f")
        with c2:
            fi     = avail.index(st.session_state.conv_from) if st.session_state.conv_from in avail else 0
            from_c = st.selectbox("From", avail, index=fi)
        with c3:
            ti   = avail.index(st.session_state.conv_to) if st.session_state.conv_to in avail else 0
            to_c = st.selectbox("To", avail, index=ti)

        st.session_state.conv_from = from_c
        st.session_state.conv_to   = to_c

        try:
            converted, rate = converter.convert(amount, from_c, to_c)
            inv = 1 / rate if rate else 0
            st.success(
                f"**{amount:,.2f} {from_c}** = **{converted:,.4f} {to_c}**\n\n"
                f"1 {from_c} = {rate:.6f} {to_c}   |   1 {to_c} = {inv:.6f} {from_c}"
            )
        except (ValueError, ZeroDivisionError) as exc:
            st.error(str(exc))
            return

        st.divider()
        st.subheader("Convert to Multiple Currencies")
        default_targets = [
            c for c in ["USD", "EUR", "GBP", "JPY", "ZAR", "GHS", "INR"]
            if c in avail and c != from_c
        ]
        targets = st.multiselect(
            "Select target currencies",
            [c for c in avail if c != from_c],
            default=default_targets[:5],
        )

        if targets:
            bulk = converter.convert_to_many(amount, from_c, targets)
            st.dataframe(
                pd.DataFrame([
                    {
                        "Currency": k,
                        "Name":      CURRENCY_NAMES.get(k, "—"),
                        "Rate":      f"{v['rate']:.6f}",
                        "Converted": f"{v['converted']:,.4f}",
                    }
                    for k, v in bulk.items()
                ]),
                use_container_width=True,
                hide_index=True,
            )

        with st.expander("Cross-Rate Matrix"):
            matrix_codes = [from_c] + [t for t in targets if t != from_c][:6]
            if len(matrix_codes) > 1:
                matrix = converter.get_rate_matrix(matrix_codes)
                df_m   = pd.DataFrame(matrix).T
                df_m.index.name = "From / To"
                st.dataframe(
                    df_m.map(lambda x: f"{x:.5f}" if x is not None else "—"),
                    use_container_width=True,
                )
            else:
                st.caption("Select at least one target currency above to see the matrix.")

    def _tab_trends(self, base: str, watchlist: List[str]) -> None:
        st.subheader("Historical Trends")

        c1, c2 = st.columns([3, 1])
        with c1:
            targets = st.multiselect(
                "Currencies to chart",
                [c for c in ALL_CURRENCY_CODES if c != base],
                default=[c for c in watchlist if c != base][:4],
            )
        with c2:
            period_label = st.selectbox("Lookback", list(self._PERIODS.keys()), index=2)

        days = self._PERIODS[period_label]

        if not targets:
            st.info("Select at least one currency above to see charts.")
            return

        history = self.store.get_history(base, targets, days=days)

        if history.empty:
            st.warning("No historical data yet. Click Refresh Rates in the sidebar.")
            return

        st.caption("Note: the first 30 days of data are simulated. Real data builds up with each refresh.")

        st.subheader("Exchange Rate Trend")
        fig1 = self.charts.build_trend_chart(history, base)
        if fig1:
            st.pyplot(fig1, use_container_width=True)

        st.divider()

        st.subheader("Annualised Volatility")
        st.caption("Higher % means the rate fluctuates more.")
        fig2 = self.charts.build_volatility_chart(history, base)
        if fig2:
            st.pyplot(fig2, use_container_width=True)

        st.divider()

        st.subheader("Weekly OHLC Candlestick")
        ohlc_target = st.selectbox("Select currency for candlestick", targets, index=0)
        fig3 = self.charts.build_candlestick_chart(history, base, ohlc_target)
        if fig3:
            st.pyplot(fig3, use_container_width=True)
        else:
            st.info("Need at least 10 days of data to draw the candlestick chart.")

    def run(self) -> None:
        base, watchlist = self._sidebar()

        try:
            rates_data = self._fetch_rates(base)
        except EnvironmentError as exc:
            st.error(str(exc))
            st.stop()
        except Exception as exc:
            st.error(f"Could not fetch rates: {exc}")
            st.stop()

        rates = rates_data.get("conversion_rates", {})

        if not self.store.has_data_for(base):
            with st.spinner("First run: generating seed history..."):
                self.store.seed_historical_data(base, rates)

        self.store.store_rates(base, rates)
        converter = CurrencyConverter(rates, base)

        st.title("FX Tracker")
        st.caption(f"Live exchange rates  |  Base currency: **{base}**")

        tab1, tab2, tab3 = st.tabs(["Dashboard", "Converter", "Trends"])
        with tab1:
            self._tab_dashboard(rates_data, watchlist, base)
        with tab2:
            self._tab_converter(converter)
        with tab3:
            self._tab_trends(base, watchlist)


if __name__ == "__main__":
    app = StreamlitFXApp()
    app.run()