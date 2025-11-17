# Stock Candidate Screening Feature

This guide explains the three-mode `screen` command that combines User Story 4 (candidate selection) and User Story 5 (strategy-symbol screening with optional conditional filtering).

## Overview

The `screen` command operates in three modes based on which flags you provide:

- **Mode A (Candidate Selection)**: Filter universe by market conditions - *no strategy evaluation*
- **Mode B (Unconditional Strategy Screening)**: Rank symbols by strategy performance on *all historical data*
- **Mode C (Conditional Strategy Screening)**: Rank symbols by strategy performance *only during specific market conditions*

## Prerequisites

- Python env with project deps installed (`python3 -m venv .venv && source .venv/bin/activate && pip install -e .`)
- Universe file: CSV with symbols or `data/universes/*.csv`
- For Mode C: Selector definition file in `selectors/*.yaml`

---

## Mode A: Candidate Selection Only (US4)

**Use Case**: "What stocks are showing interesting conditions RIGHT NOW that I should look at tomorrow?"

### What It Does
- Filters universe by market conditions (gaps, volume spikes, volatility)
- Returns symbols matching conditions in recent bars
- **No strategy evaluation** - just condition detection
- Forward-looking: identifies current opportunities

### Example: Find Gap-Down Stocks with Volume Spikes

```bash
python -m quant_scenario_engine.cli.main screen \
  --universe data/universes/sp500.csv \
  --gap-min 0.03 \
  --volume-z-min 1.5 \
  --top 20
```

**Output**: 20 symbols currently showing ≥3% gap with volume spike

### Example: Use Inline Symbol List

```bash
python -m quant_scenario_engine.cli.main screen \
  --universe "['AAPL','MSFT','TSLA','NVDA','META']" \
  --gap-min 0.02 \
  --volume-z-min 2.0 \
  --horizon 10
```

### Mode A CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--universe` | PATH or list | Required | CSV file or inline list of symbols |
| `--gap-min` | FLOAT | 0.03 | Minimum absolute gap percentage |
| `--volume-z-min` | FLOAT | 1.5 | Minimum volume z-score |
| `--horizon` | INT | 10 | Episode horizon (bars) |
| `--top` | INT | All | Keep top N candidates by score |
| `--max-workers` | INT | 4 | Parallel workers (clamped ≤6) |

### Mode A Output

```json
{
  "mode": "candidate_selection",
  "selector_name": "gap_volume",
  "candidates": [
    {
      "symbol": "TSLA",
      "t0": "2024-01-15",
      "horizon": 10,
      "selector": "gap_volume",
      "state_features": {
        "gap_pct": -0.042,
        "volume_z": 2.3
      },
      "score": 4.72
    }
  ]
}
```

---

## Mode B: Unconditional Strategy Screening (US5)

**Use Case**: "Which stocks historically work BEST with my strategy overall?"

### What It Does
- Backtests strategy on ALL historical data for each symbol
- Computes metrics: sharpe, mean_pnl, sortino, max_drawdown
- Ranks symbols by specified metric
- Returns top N symbols where strategy performed best

### Example: Find Best Stocks for SMA Trend Strategy

```bash
python -m quant_scenario_engine.cli.main screen \
  --universe data/universes/sp500.csv \
  --strategy stock_sma_trend \
  --rank-by sharpe \
  --top 20 \
  --lookback-years 5
```

**Output**: Top 20 stocks where SMA trend strategy had highest Sharpe ratio over last 5 years

### Example: Rank by Mean P&L

```bash
python -m quant_scenario_engine.cli.main screen \
  --universe data/universes/nasdaq100.csv \
  --strategy stock_rsi_reversion \
  --rank-by mean_pnl \
  --top 10
```

### Mode B CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--universe` | PATH or list | Required | CSV file or inline list of symbols |
| `--strategy` | STRING | Required | Strategy name (e.g., stock_sma_trend) |
| `--rank-by` | ENUM | sharpe | Metric: sharpe, mean_pnl, sortino, max_drawdown, cvar |
| `--top` | INT | All | Return top N ranked symbols |
| `--lookback-years` | FLOAT | 5 | Years of historical data to evaluate |
| `--max-workers` | INT | 4 | Parallel workers (clamped ≤6) |

### Mode B Output

```json
{
  "mode": "unconditional_strategy",
  "strategy": "stock_sma_trend",
  "rank_by": "sharpe",
  "ranked_symbols": [
    {
      "symbol": "NVDA",
      "rank": 1,
      "metrics": {
        "mean_pnl": 1243.56,
        "sharpe": 1.82,
        "sortino": 2.34,
        "max_drawdown": -0.23
      },
      "confidence": "high"
    },
    {
      "symbol": "AAPL",
      "rank": 2,
      "metrics": {
        "mean_pnl": 987.23,
        "sharpe": 1.67,
        "sortino": 2.01,
        "max_drawdown": -0.18
      },
      "confidence": "high"
    }
  ]
}
```

---

## Mode C: Conditional Strategy Screening (US5)

**Use Case**: "Which stocks work BEST with my strategy WHEN specific market conditions occur?"

### What It Does
- Backtests strategy ONLY on episodes where selector conditions met
- Evaluates strategy performance during gaps, breakouts, volatility spikes, etc.
- Ranks symbols by conditional performance
- Flags low-confidence results (< 10 episodes)

### Example: Best Stocks for SMA Trend During Gap-Downs

```bash
python -m quant_scenario_engine.cli.main screen \
  --universe data/universes/sp500.csv \
  --strategy stock_sma_trend \
  --rank-by sharpe \
  --conditional-file selectors/gap_down_volume_spike.yaml \
  --top 20
```

**Output**: Top 20 stocks where SMA trend performed best specifically during gap-down + volume spike events

### Example: Using Inline Selector Parameters

```bash
python -m quant_scenario_engine.cli.main screen \
  --universe data/universes/tech_growth.csv \
  --strategy stock_rsi_reversion \
  --rank-by mean_pnl \
  --gap-min 0.03 \
  --volume-z-min 2.0 \
  --top 15 \
  --min-episodes 10
```

### Mode C CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--universe` | PATH or list | Required | CSV file or inline list of symbols |
| `--strategy` | STRING | Required | Strategy name |
| `--rank-by` | ENUM | sharpe | Ranking metric |
| `--conditional-file` | PATH | Optional | Path to selector YAML (e.g., selectors/gap_down_volume_spike.yaml) |
| `--gap-min` | FLOAT | 0.03 | Inline selector: minimum gap |
| `--volume-z-min` | FLOAT | 1.5 | Inline selector: minimum volume z-score |
| `--min-episodes` | INT | 10 | Warn if symbol has fewer episodes |
| `--top` | INT | All | Return top N ranked symbols |
| `--lookback-years` | FLOAT | 5 | Years of historical data |
| `--max-workers` | INT | 4 | Parallel workers |

### Selector YAML Format

Create reusable selector definitions in `selectors/*.yaml`:

**File: `selectors/gap_down_volume_spike.yaml`**
```yaml
name: gap_down_volume_spike
description: "Large gap down with significant volume spike"
parameters:
  gap_min: 0.03
  volume_z_min: 1.5
  horizon: 10
logic: "gap_pct < -gap_min AND volume_z_score > volume_z_min"
```

**File: `selectors/breakout_momentum.yaml`**
```yaml
name: breakout_momentum
description: "Price breaks above SMA(50) with momentum"
parameters:
  sma_period: 50
  momentum_threshold: 0.02
  volume_z_min: 1.0
logic: "close > sma_50 AND ((close - close[1]) / close[1]) > momentum_threshold AND volume_z > volume_z_min"
```

### Mode C Output

```json
{
  "mode": "conditional_strategy",
  "strategy": "stock_sma_trend",
  "rank_by": "sharpe",
  "selector_name": "gap_down_volume_spike",
  "ranked_symbols": [
    {
      "symbol": "TSLA",
      "rank": 1,
      "metrics": {
        "mean_pnl": 856.34,
        "sharpe": 1.45,
        "sortino": 1.89,
        "max_drawdown": -0.31
      },
      "episode_count": 47,
      "confidence": "high"
    },
    {
      "symbol": "AMD",
      "rank": 2,
      "metrics": {
        "mean_pnl": 723.12,
        "sharpe": 1.28,
        "sortino": 1.67,
        "max_drawdown": -0.28
      },
      "episode_count": 8,
      "confidence": "low"
    }
  ]
}
```

**Note**: AMD has `confidence: "low"` due to only 8 episodes (< min_episodes threshold of 10)

---

## Mode Detection Logic

The CLI automatically detects which mode to run based on flags:

```python
if not args.strategy:
    # Mode A: Candidate Selection Only (US4)
    run_candidate_selection()
elif args.strategy and not (args.conditional_file or inline_selector_params):
    # Mode B: Unconditional Strategy Screening
    run_unconditional_strategy_screen()
elif args.strategy and (args.conditional_file or inline_selector_params):
    # Mode C: Conditional Strategy Screening
    run_conditional_strategy_screen()
```

---

## Common Workflows

### Workflow 1: Find Today's Opportunities + Backtest Them

**Step 1**: Mode A - Find stocks with interesting conditions today
```bash
screen --universe sp500.csv --gap-min 0.03 --top 20 > today_candidates.json
```

**Step 2**: Mode B - Check which have good historical strategy fit
```bash
screen --universe today_candidates.json --strategy stock_sma_trend --rank-by sharpe
```

### Workflow 2: Optimize Strategy-Symbol Pairing

**Step 1**: Mode B - Find best 50 stocks for strategy overall
```bash
screen --universe sp500.csv --strategy stock_sma_trend --top 50 > sma_best50.json
```

**Step 2**: Mode C - Narrow to best 10 during gap conditions
```bash
screen --universe sma_best50.json --strategy stock_sma_trend \
  --conditional-file selectors/gap_down_volume_spike.yaml --top 10
```

### Workflow 3: Compare Unconditional vs Conditional Performance

```bash
# Unconditional
screen --universe nasdaq100.csv --strategy stock_rsi_reversion \
  --rank-by sharpe --top 20 > unconditional.json

# Conditional
screen --universe nasdaq100.csv --strategy stock_rsi_reversion \
  --rank-by sharpe --conditional-file selectors/oversold_spike.yaml \
  --top 20 > conditional.json

# Compare results side-by-side
```

---

## Output Files and Naming

Results are saved to `runs/<run_id>/` with mode-specific naming:

- **Mode A**: `screen_results_candidates.json`
- **Mode B**: `screen_results_unconditional.json`
- **Mode C**: `screen_results_conditional_<selector_name>.json`

Metadata includes:
- Mode executed
- Strategy name (Modes B/C)
- Selector name (Modes A/C)
- Episode counts per symbol (Mode C)
- Confidence levels (Mode C)
- Timestamp and run parameters

---

## Programmatic Usage

### Mode A (Python API)
```python
from quant_scenario_engine.simulation.screen import screen_candidates
from quant_scenario_engine.selectors.gap_volume import GapVolumeSelector

selector = GapVolumeSelector(gap_min=0.03, volume_z_min=1.5)
candidates = screen_candidates(
    universe=['AAPL', 'MSFT', 'TSLA'],
    selector=selector,
    top_n=20
)
```

### Mode B (Python API)
```python
from quant_scenario_engine.simulation.screen import run_strategy_screen

results = run_strategy_screen(
    universe=['AAPL', 'MSFT', 'NVDA', ...],  # or path to CSV
    strategy='stock_sma_trend',
    rank_by='sharpe',
    lookback_years=5,
    top_n=20
)
print(results.ranked_symbols)
```

### Mode C (Python API)
```python
from quant_scenario_engine.simulation.screen import run_strategy_screen
from quant_scenario_engine.selectors.loader import load_selector

selector = load_selector('selectors/gap_down_volume_spike.yaml')
results = run_strategy_screen(
    universe='data/universes/sp500.csv',
    strategy='stock_sma_trend',
    rank_by='sharpe',
    conditional=True,
    selector=selector,
    min_episodes=10,
    top_n=20
)
print(results.ranked_symbols)
```

---

## Confidence Levels (Mode C)

Symbols are flagged with confidence based on episode count:

| Episode Count | Confidence | Interpretation |
|---------------|------------|----------------|
| ≥30 | `high` | Statistically robust results |
| 10-29 | `medium` | Acceptable but limited data |
| <10 | `low` | Insufficient episodes - results may be unreliable |

---

## Notes and Best Practices

- **Missing Data**: Symbols with missing or insufficient data are skipped with warnings logged
- **Parallel Execution**: `max_workers` is clamped to ≤6 per FR-018 to respect VPS resource limits
- **Selector Sparsity**: If most symbols have <10 episodes in Mode C, consider relaxing selector thresholds
- **Inline vs File Selectors**: Use inline params for quick tests, YAML files for production/reusable definitions
- **Universe Management**: Store curated universes in `data/universes/` for easy reuse
- **Result Caching**: Historical backtests can be cached to speed up repeated Mode B/C runs on same universe

---

## Troubleshooting

**Issue**: "No episodes found for any symbol"
- **Solution**: Relax selector thresholds (lower `gap_min`, `volume_z_min`)

**Issue**: "All symbols have low confidence"
- **Solution**: Increase `lookback_years` or use broader selector criteria

**Issue**: "Strategy evaluation very slow"
- **Solution**: Increase `max_workers` (up to 6) or reduce `lookback_years`

**Issue**: "Results differ between unconditional and conditional"
- **Expected**: Conditional filters to specific episodes - rankings should differ
- **Verify**: Check episode counts and ensure selector is triggering as expected

---

## Related Documentation

- **US4 Acceptance Scenarios**: `specs/001-mvp-pipeline/spec.md` lines 50-60
- **US5 Acceptance Scenarios**: `specs/001-mvp-pipeline/spec.md` lines 63-114
- **Implementation Tasks**: `specs/001-mvp-pipeline/tasks.md` Phase 5 (US5)
- **API Contracts**: `specs/001-mvp-pipeline/contracts/openapi.yaml` ScreenRequest/ScreenResponse
- **Selector Definitions**: `selectors/*.yaml` (create your own!)
