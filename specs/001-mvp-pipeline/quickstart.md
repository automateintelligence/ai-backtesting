# Quickstart

1) **Environment**
- Python 3.11 on Linux VPS (8 vCPU, 24 GB RAM). 
- Create venv: `python3 -m venv .venv && source .venv/bin/activate`.
- Install runtime deps (draft): `pip install numpy pandas scipy numba statsmodels arch pandas-ta quantstats plotly typer[all] yfinance py_vollib`.

2) **Data prep**
- Fetch baseline OHLCV: `python -m backtesting.cli.fetch --symbol AAPL --start 2018-01-01 --end 2024-12-31 --interval 1d --target data/` (expects yfinance adapter; writes Parquet partitioned by symbol/interval).
- Optional: place Schwab-derived Parquet under matching partitions; keep `_v2` suffix when schema/source changes.

3) **Run baseline stock vs option MC comparison**
- `python -m backtesting.cli.compare --symbol AAPL --paths 1000 --steps 60 --distribution laplace --strategy stock_basic --option-strategy call_basic --iv 0.25 --seed 42`
- Outputs: run directory `runs/<run_id>/` with `metrics.json/csv`, `run_meta.json`, optional plots.

4) **Parameter grid exploration**
- `python -m backtesting.cli.grid --symbol AAPL --config configs/grid_aapl.yaml --max-workers 6`
- Config defines strategy param grid (thresholds, DTE, strike offsets). Produces ranked objective scores per config.

5) **Candidate screening + conditional backtest**
- `python -m backtesting.cli.screen --universe configs/universe.yaml --selector configs/selector_gap.yaml --lookback 5y --top 20`
- `python -m backtesting.cli.conditional --symbol AAPL --selector configs/selector_gap.yaml --paths 1000 --steps 60 --seed 99`
- Screening outputs candidate episodes; conditional run backtests only on those episodes and reports stock vs option metrics.

6) **Replay a run**
- `python -m backtesting.cli.compare --replay runs/<run_id>/run_meta.json`
- Reuses seed/params and persisted MC (if available) to reproduce metrics; warns if historical data changed.

7) **Resource safeguards**
- By default, MC stays in-memory when estimated footprint <25% RAM; otherwise memmap/npz is used automatically.
- Workers capped at 6 on 8-core VPS; override with `--max-workers` subject to FR-018 guardrails.

> CLI module names/flags are placeholders for implementation; map them to the concrete Typer commands during coding.
