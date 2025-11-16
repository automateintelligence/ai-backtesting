# Data Model

## Entities

### DataSource
- **Fields**: `name` (enum: yfinance, schwab_stub), `symbols` (list[str]), `start` (date), `end` (date), `interval` (enum: 1d, 5m, 1m), `source_version` (str), `path` (abs path to Parquet partition)
- **Validation**: Must provide OHLCV columns; interval must match requested frequency; warn and drop symbols with insufficient coverage.
- **Relationships**: Provides input to `ReturnDistribution` fitting and `CandidateSelector` screening.

### ReturnDistribution
- **Fields**: `model` (enum: laplace, student_t, garch_t), `params` (dict), `fit_window` (int bars), `seed` (int), `aic`/`bic` (float, optional), `fit_status` (enum: success, warn, fail)
- **Validation**: Parameter dict must match model; seed required for reproducibility; fail if sample < minimum bars.
- **Relationships**: Generates `PricePath` samples; metadata written into `SimulationRun.run_meta`.

### PricePath
- **Fields**: `paths` (np.ndarray | memmap), `n_paths` (int), `n_steps` (int), `s0` (float), `storage` (enum: memory, npz, memmap), `seed` (int)
- **Validation**: `n_paths*n_steps*sizeof(float)` must respect RAM thresholds (<25% in-memory, ≥25% triggers memmap/npz); required seed for replay.
- **Relationships**: Consumed by `Strategy` evaluations and option pricers.

### StrategyParams
- **Fields**: `name` (str), `kind` (enum: stock, option), `params` (dict of typed values), `position_sizing` (enum: fixed_notional, percent_equity), `fees` (float), `slippage` (float)
- **Validation**: Validate param schema per strategy; disallow negative sizing; ensure DTE/strike offsets valid for option strategies.
- **Relationships**: Drives `StrategySignals` and links to `OptionSpec` when `kind=option`.

### OptionSpec
- **Fields**: `option_type` (enum: call, put), `strike` (float or offset), `maturity_days` (int), `implied_vol` (float), `risk_free_rate` (float), `contracts` (int)
- **Validation**: Maturity ≥ simulation horizon; IV > 0; strike positive; contracts non-zero; warning when IV source missing.
- **Relationships**: Passed to `OptionPricer`; tied to `StrategyParams` for option strategies.

### StrategySignals
- **Fields**: `signals_stock` (array[n_paths, n_steps] int {-1,0,1}), `signals_option` (array[n_paths, n_steps] int {-1,0,1}), `option_spec` (OptionSpec), `features_used` (list[str])
- **Validation**: Shapes must match PricePath; option_spec required if option signals non-empty.
- **Relationships**: Produced by `Strategy` components; consumed by `SimulationRun`.

### CandidateSelector
- **Fields**: `name` (str), `rules` (list of predicates e.g., gap %, volume z-score), `feature_requirements` (list[str]), `min_lookback` (int)
- **Validation**: Rules must only use info available at time t; feature deps resolved before evaluation; warn on missing features.
- **Relationships**: Generates `CandidateEpisode` sets; conditions both historical backtests and conditional MC.

### CandidateEpisode
- **Fields**: `symbol` (str), `t0` (timestamp), `horizon` (int bars), `state_features` (dict[str, float]), `selector_name` (str)
- **Validation**: t0 must exist in historical data; horizon >0; state_features complete per selector spec.
- **Relationships**: Feeds conditional backtests and conditional MC sampling.

### SimulationRun
- **Fields**: `run_id` (uuid/str), `symbol` (str or list), `config` (RunConfig), `distribution` (ReturnDistribution), `price_paths` (PricePath), `strategies` (list[StrategyParams]), `episodes` (list[CandidateEpisode]|null), `artifacts_path` (abs path)
- **Validation**: Requires run_id uniqueness; config must specify seed; for conditional runs, episodes list cannot be empty (else fallback path documented).
- **Relationships**: Owns lifecycle of MC generation, strategy execution, and handoff to `MetricsReport`.

### RunConfig
- **Fields**: `n_paths` (int), `n_steps` (int), `seed` (int), `distribution_model` (str), `data_source` (str), `selector` (CandidateSelector|null), `grid` (list[StrategyParams]|null), `resource_limits` (workers, mem_threshold)
- **Validation**: Enforce FR-018 limits; reject configs exceeding RAM/time estimates; seed required for reproducibility.
- **Relationships**: Stored within `SimulationRun` and metadata file for replay.

### MetricsReport
- **Fields**: `per_config_metrics` (list of `{config_id, pnl_stats, drawdown, var, cvar, sharpe, sortino, objective}`), `comparison` (stock vs option summary), `conditional_metrics` (episode-level stats), `logs_path` (str), `plots` (optional paths)
- **Validation**: Objective function defined; metrics arrays align with configs; conditional metrics only when episodes provided.
- **Relationships**: Generated from `SimulationRun`; persisted as JSON/CSV; referenced by quickstart/CLI outputs.

## Relationships Overview
- `DataSource` → `ReturnDistribution` → `PricePath` → `StrategySignals` → `SimulationRun` → `MetricsReport`.
- `CandidateSelector` → `CandidateEpisode` feeds both conditional backtests and conditional MC sampling.
- `RunConfig` ties all components together and is persisted for replay.

## State & Lifecycle
1. Load OHLCV from `DataSource` (validate schema).
2. Fit `ReturnDistribution` (persist params/seed).
3. Generate `PricePath` (select storage policy based on RAM threshold).
4. Produce `StrategySignals` (feature-enriched as configured; includes OptionSpec when needed).
5. Execute `SimulationRun` (stock + option strategies, grid optional) over unconditional or conditional episodes.
6. Emit `MetricsReport` + artifacts + `run_meta.json` for reproducibility.
7. Optional replay uses `run_meta.json` and persisted MC data if available; otherwise regenerates with same seed/params.
