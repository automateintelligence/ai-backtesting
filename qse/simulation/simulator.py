"""Market simulator for stock and option strategies."""

from __future__ import annotations

import numpy as np

from qse.exceptions import BankruptcyError
from qse.pricing.black_scholes import BlackScholesPricer
from qse.schema.signals import StrategySignals
from qse.simulation.metrics import MetricsReport, compute_metrics


class MarketSimulator:
    def __init__(self, pricer: BlackScholesPricer | None = None) -> None:
        self.pricer = pricer or BlackScholesPricer()

    def _detect_bankruptcy(self, price_paths: np.ndarray) -> tuple[np.ndarray, float]:
        bankrupt_mask = (price_paths <= 0).any(axis=1)
        return bankrupt_mask, float(bankrupt_mask.mean()) if price_paths.size else 0.0

    def simulate_stock(self, price_paths: np.ndarray, signals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        # P&L from signed price deltas; prepend first bar to align dimensions
        deltas = np.diff(price_paths, axis=1, prepend=price_paths[:, :1])
        step_pnl = signals * deltas
        pnl = step_pnl.sum(axis=1)
        equity_paths = price_paths[:, :1] + np.cumsum(step_pnl, axis=1)
        return pnl, equity_paths

    def simulate_option(self, price_paths: np.ndarray, signals: np.ndarray, option_spec) -> tuple[np.ndarray, np.ndarray]:
        pricer = self.pricer
        option_prices = np.vstack([pricer.price(path, option_spec) for path in price_paths])
        deltas = np.diff(option_prices, axis=1, prepend=option_prices[:, :1])
        step_pnl = signals * deltas
        pnl = step_pnl.sum(axis=1)
        equity_paths = option_prices[:, :1] + np.cumsum(step_pnl, axis=1)
        return pnl, equity_paths

    def run(
        self,
        price_paths: np.ndarray,
        signals: StrategySignals,
        *,
        var_method: str = "historical",
        covariance_estimator: str = "sample",
        lookback_window: int | None = None,
    ) -> MetricsReport:
        bankrupt_mask, bankruptcy_rate = self._detect_bankruptcy(price_paths)
        if bankrupt_mask.any():
            # Replace non-positive paths with epsilon to allow metrics to continue
            price_paths = price_paths.copy()
            price_paths[bankrupt_mask] = np.clip(price_paths[bankrupt_mask], 1e-9, None)
            if bankruptcy_rate > 0.5:
                raise BankruptcyError("More than half of simulated paths went bankrupt")

        stock_pnl, stock_equity_paths = self.simulate_stock(price_paths, signals.signals_stock)
        option_pnl = np.zeros_like(stock_pnl)
        option_equity_paths = np.zeros_like(stock_equity_paths)

        early_exercise_events = 0
        if signals.option_spec is not None:
            option_pnl, option_equity_paths = self.simulate_option(
                price_paths, signals.signals_option, signals.option_spec
            )
            early_exercise_events = int(getattr(signals.option_spec, "early_exercise", False))

        combined_equity_paths = stock_equity_paths + option_equity_paths
        equity_curve_mean = combined_equity_paths.mean(axis=0)

        combined_pnl = stock_pnl + option_pnl
        return compute_metrics(
            combined_pnl,
            equity_curve_mean,
            var_method=var_method,  # type: ignore[arg-type]
            covariance_estimator=covariance_estimator,  # type: ignore[arg-type]
            lookback_window=lookback_window,
            bankruptcy_rate=bankruptcy_rate,
            early_exercise_events=early_exercise_events,
        )

    def run_episodes(
        self,
        price_paths: np.ndarray,
        signals: StrategySignals,
        episodes: list[tuple[int, int]],
        *,
        var_method: str = "historical",
        covariance_estimator: str = "sample",
    ) -> list[MetricsReport]:
        """Evaluate metrics for each [start, end] episode window (inclusive)."""

        results: list[MetricsReport] = []
        for start, end in episodes:
            start_idx = max(0, start)
            end_idx = min(price_paths.shape[1], end)
            if end_idx - start_idx < 2:
                continue
            window_prices = price_paths[:, start_idx:end_idx]
            window_signals_stock = signals.signals_stock[:, start_idx:end_idx]
            window_signals_option = signals.signals_option[:, start_idx:end_idx]
            window_signals = StrategySignals(
                signals_stock=window_signals_stock,
                signals_option=window_signals_option,
                option_spec=signals.option_spec,
                features_used=signals.features_used,
            )
            metrics = self.run(
                window_prices,
                window_signals,
                var_method=var_method,
                covariance_estimator=covariance_estimator,
                lookback_window=None,
            )
            results.append(metrics)
        return results
