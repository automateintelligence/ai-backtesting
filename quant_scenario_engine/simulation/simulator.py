"""Market simulator for stock and option strategies."""

from __future__ import annotations

import numpy as np

from quant_scenario_engine.exceptions import BankruptcyError
from quant_scenario_engine.pricing.black_scholes import BlackScholesPricer
from quant_scenario_engine.schema.signals import StrategySignals
from quant_scenario_engine.simulation.metrics import MetricsReport, compute_metrics


class MarketSimulator:
    def __init__(self) -> None:
        self.pricer = BlackScholesPricer()

    def simulate_stock(self, price_paths: np.ndarray, signals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        pnl = (signals * np.diff(price_paths, axis=1, prepend=price_paths[:, :1])).sum(axis=1)
        equity = price_paths[:, -1]
        return pnl, equity

    def simulate_option(self, price_paths: np.ndarray, signals: np.ndarray, option_spec) -> tuple[np.ndarray, np.ndarray]:
        pricer = self.pricer
        option_prices = []
        for path in price_paths:
            option_prices.append(pricer.price(path, option_spec))
        option_prices = np.vstack(option_prices)
        pnl = (signals * np.diff(option_prices, axis=1, prepend=option_prices[:, :1])).sum(axis=1)
        equity = option_prices[:, -1]
        return pnl, equity

    def run(self, price_paths: np.ndarray, signals: StrategySignals) -> MetricsReport:
        if (price_paths <= 0).any():
            raise BankruptcyError("Non-positive prices encountered")

        stock_pnl, stock_equity = self.simulate_stock(price_paths, signals.signals_stock)
        option_pnl = np.zeros_like(stock_pnl)
        option_equity = np.zeros_like(stock_equity)

        if signals.option_spec is not None:
            option_pnl, option_equity = self.simulate_option(
                price_paths, signals.signals_option, signals.option_spec
            )

        combined_equity = stock_equity + option_equity
        combined_pnl = stock_pnl + option_pnl
        return compute_metrics(combined_pnl, combined_equity)

