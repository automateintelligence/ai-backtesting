# Stock Candidate Screening Feature

This guide explains how to run the User Story 4 screening flow (gap + volume selector) to produce candidate episodes for later backtesting/conditional MC.

## Prereqs
- Python env with project deps installed (`python3 -m venv .venv && source .venv/bin/activate && pip install -e .`).
- CSV universe with columns: `symbol,date,open,high,low,close,volume` (date parsable by pandas).

## Quickstart (CLI)
```bash
python -m quant_scenario_engine.cli.main screen \
  --universe data/universe_sample.csv \
  --gap-min 0.03 \
  --volume-z-min 1.5 \
  --horizon 10 \
  --top 50 \
  --max-workers 4
```

### Alternative: fetch + screen in one call
```bash
python -m quant_scenario_engine.cli.main screen \
  --symbols AAPL,MSFT,TSLA \
  --start 2018-01-01 \
  --end 2024-12-31 \
  --interval 1d \
  --gap-min 0.03 \
  --volume-z-min 1.5 \
  --horizon 10 \
  --top 50
```
This downloads missing OHLCV to `data/historical/interval={interval}/symbol={symbol}/_v1/data.parquet`, extends existing files when the requested window is longer/newer, or slices a shorter window directly from the Parquet cache.

### Alternative: inline list for symbols (Python/JSON-style)
```bash
python -m quant_scenario_engine.cli.main screen \
  --universe "['B','ABEV','COMP','MRK','T','IVVD']" \
  --start 2018-01-01 \
  --end 2024-12-31 \
  --interval 1d \
  --gap-min 0.03 \
  --volume-z-min 1.5 \
  --horizon 10 \
  --top 50 \
  --max-workers 4
```
The inline list is parsed as a symbol list when `--universe` is not a CSV path. Comma-separated strings also work (`--symbols B,ABEV,...`).

## What it does
- Enriches each symbol’s OHLCV with SMA/RSI/volume_z and `gap_pct` features (`features.pipeline.enrich_ohlcv`).
- Applies `GapVolumeSelector` (abs(gap) ≥ `gap_min`, volume_z ≥ `volume_z_min`) to each symbol, scores by `|gap| + max(volume_z,0)`, sorts, and collects episodes with horizon `horizon`.
- Parallelizes per symbol with worker clamp to 6 to respect FR-018.
- Returns JSON payload of candidates matching contracts/openapi ScreenResponse.

## CLI arguments
- `--universe PATH` (required): CSV input.
- `--gap-min FLOAT` (default 0.03): Minimum absolute gap percentage.
- `--volume-z-min FLOAT` (default 1.5): Minimum volume z-score.
- `--horizon INT` (default 10): Episode horizon (bars); must be > 0.
- `--top INT` (optional): Keep top N candidates by score across all symbols.
- `--max-workers INT` (default 4): Parallel workers, clamped to ≤6.
- `--symbols TEXT` (comma separated): Alternative to `--universe`; fetches data automatically.
- `--start/--end DATE` (YYYY-MM-DD): Required when using `--symbols`.
- `--interval TEXT`: Data interval (1m..1mo). Must match cache directory; shorter requested windows are served from existing Parquet when available.

## Output
- Printed JSON with `candidates` list: `{symbol, t0, horizon, selector, state_features, score}` where `state_features` includes `gap_pct` and `volume_z`.
- Logs emitted in JSON (component `cli_screen` and `screen`).

## Useful modules (for programmatic use)
- `quant_scenario_engine.features.pipeline.enrich_ohlcv(df)` → adds indicators.
- `quant_scenario_engine.selectors.gap_volume.GapVolumeSelector(...).select(df)` → episodes for a single symbol.
- `quant_scenario_engine.simulation.screen.screen_universe(universe, selector, max_workers, top_n)` → batch screening.
- `quant_scenario_engine.schema.screen.ScreenResponse` → JSON serialization helper.

## Notes
- Missing required columns in universe CSV will cause exit code 1.
- When required selector features are absent, selector logs a warning and returns no episodes.
- If produced episodes < `min_episodes` (default 30), a warning is logged (per FR-CAND-006/SC-020); caller decides whether to continue.
- When using `--symbols`, data files are reused when the requested window is fully covered; otherwise they are extended. Shorter windows are read via Parquet filtering instead of re-downloading.
- If `--universe` points to a CSV path it is used directly; if it looks like a list (e.g., `['AAPL','MSFT']`) it is treated as symbols input and fetched.
