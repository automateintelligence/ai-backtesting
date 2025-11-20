## How to Inspect Strategy Positions

After running a `compare` command, you want to see what the strategy actually did. Here's how:

### Method 1: Use the Analysis Script (Easiest)

```bash
python examples/analyze_strategy_positions.py
```

This will show you:
- **Signal Summary**: How many trades, time in market, position sizes
- **Position History**: Entry/exit points with prices for specific paths
- **Trading Activity**: Detailed statistics across all paths

**Example Output**:
```
STOCK STRATEGY:
  Total trades: 348
  Avg trades/path: 3.5
  Time in market: 73.4% (44/60 steps)
  Average position size: 110 shares
  Max position size: 127 shares

POSITION HISTORY - Path 0 (stock):
Step   Type       Before       After        Price      Change
--------------------------------------------------------------------------------
1      entry               0 shares        108 shares   $102.55    +108 shares
```

---

### Method 2: Programmatic Analysis

```python
from qse.distributions.factory import get_distribution
from qse.models.options import OptionSpec
from qse.simulation.compare import run_compare
from qse.analysis.signals import (
    generate_signal_summary,
    print_position_history,
)
import numpy as np

# Setup and run
dist = get_distribution("laplace")
dist.fit(np.random.laplace(0, 0.02, size=500))

result = run_compare(
    s0=100.0,
    distribution=dist,
    n_paths=100,
    n_steps=60,
    seed=42,
    stock_strategy="stock_sma_trend",
    option_strategy="option_atm_call_momentum",
    option_spec=OptionSpec(
        option_type="call",
        strike=100.0,
        maturity_days=30,
        implied_vol=0.25,
        risk_free_rate=0.01,
        contracts=1,
    ),
)

# Extract signals
stock_signals = result.signals.signals_stock
option_signals = result.signals.signals_option

# Regenerate price paths (or store in RunResult)
from qse.mc.generator import generate_price_paths
price_paths = generate_price_paths(
    s0=100.0, distribution=dist, n_paths=100, n_steps=60, seed=42
)

# Print summary
summary = generate_signal_summary(stock_signals, option_signals, price_paths)
print(summary)

# Print position history for path 0
print_position_history(stock_signals, price_paths, path_idx=0, signal_type="stock")
print_position_history(option_signals, price_paths, path_idx=0, signal_type="option")
```

---

### Method 3: Save Signals to File for Later Analysis

```python
import numpy as np

# After running compare...
np.savez(
    'signals_tsla.npz',
    stock=result.signals.signals_stock,
    option=result.signals.signals_option,
    prices=price_paths
)

# Load later
data = np.load('signals_tsla.npz')
stock_signals = data['stock']
option_signals = data['option']
prices = data['prices']

# Analyze
from qse.analysis.signals import analyze_signals

stock_analysis = analyze_signals(stock_signals, prices, "stock")
print(f"Stock strategy made {stock_analysis['total_changes']} trades")
print(f"Average position: {stock_analysis['mean_position_size']:.0f} shares")
```

---

### Understanding the Signal Arrays

Signals are numpy arrays with shape `[n_paths, n_steps]`:

```python
stock_signals[path, step] = position_size
```

- **Positive value**: Long position (e.g., `108` = long 108 shares)
- **Zero**: No position (flat)
- **Negative value**: Short position (e.g., `-50` = short 50 shares)

**Example**:
```python
stock_signals[0, 10] = 108   # Path 0, step 10: long 108 shares
stock_signals[0, 11] = 108   # Still holding
stock_signals[0, 12] = 0     # Exited position (flat)
```

---

### Key Functions in `qse.analysis.signals`

#### `analyze_signals(signals, price_paths, signal_type)`
Returns dictionary with:
- `total_changes`: Total number of position changes
- `mean_changes_per_path`: Average trades per path
- `pct_time_in_position`: Percentage of time in market
- `mean_position_size`: Average position size when active
- `max_position_size`: Largest position taken

#### `print_position_history(signals, price_paths, path_idx, signal_type)`
Prints table of all entry/exit events for a specific path:
```
Step   Type       Before       After        Price      Change
--------------------------------------------------------------------------------
2      entry               0 contracts             4 contracts    $107.40    +4 contracts
10     exit                4 contracts             0 contracts    $114.65    -4 contracts
```

#### `extract_position_changes(signals, price_paths, path_indices)`
Returns list of `PositionChange` objects with:
- `step`: Which step the change occurred
- `path`: Which path
- `position_before/after`: Position sizes
- `price`: Price at which change occurred
- `change_type`: "entry", "exit", "increase", "decrease"

#### `position_changes_to_dataframe(changes)`
Converts position changes to pandas DataFrame for easy filtering/analysis.

---

### Example: Analyzing Your TSLA Run

To see what happened in your TSLA run:

**Step 1**: Modify the compare command to run programmatically and capture signals

```python
from qse.distributions.factory import get_distribution
from qse.models.options import OptionSpec
from qse.simulation.compare import run_compare
import numpy as np

# Setup distribution
dist = get_distribution("laplace")
dist.fit(np.random.laplace(0, 0.02, size=500))

# Run with same parameters as your CLI command
result = run_compare(
    s0=100.0,  # Assuming starting price (use actual TSLA price if known)
    distribution=dist,
    n_paths=500,
    n_steps=60,
    seed=42,
    stock_strategy="stock_sma_trend",
    option_strategy="option_atm_call_momentum",
    option_spec=OptionSpec(
        option_type="call",
        strike=100.0,  # Use actual strike
        maturity_days=30,
        implied_vol=0.25,
        risk_free_rate=0.01,
        contracts=1,
    ),
)

print("Metrics:", result.metrics)
```

**Step 2**: Analyze signals

```python
from qse.analysis.signals import generate_signal_summary
from qse.mc.generator import generate_price_paths

# Regenerate price paths with same seed
price_paths = generate_price_paths(
    s0=100.0, distribution=dist, n_paths=500, n_steps=60, seed=42
)

# Get summary
summary = generate_signal_summary(
    result.signals.signals_stock,
    result.signals.signals_option,
    price_paths
)
print(summary)
```

**Step 3**: Inspect specific paths

```python
from qse.analysis.signals import print_position_history

# Look at paths with best/worst performance
# (You'd need to calculate P&L per path to find these)

print_position_history(
    result.signals.signals_stock,
    price_paths,
    path_idx=0,  # First path
    signal_type="stock",
    max_rows=50
)
```

---

### Common Questions

**Q: Why does my strategy have 73% time in market but negative returns?**
- **A**: The strategy is in position frequently but timing is poor. Check if:
  - Entries happen at high prices (buying tops)
  - Exits happen at low prices (selling bottoms)
  - Position sizes are too large relative to price moves

**Q: How do I know if I'm over-trading?**
- **A**: Look at `mean_changes_per_path`:
  - **< 5**: Low activity (trend following)
  - **5-20**: Moderate activity
  - **> 20**: High activity (may be whipsawing) ← Problem area

**Q: What's a good time-in-market percentage?**
- **A**: Depends on strategy:
  - **Trend following**: 30-60% (wait for trends)
  - **Mean reversion**: 20-40% (opportunistic)
  - **Momentum**: 40-70% (stay with trends)

**Q: How can I see which paths lost the most money?**
- **A**: Calculate P&L per path and sort:
```python
# Calculate final portfolio values per path (simplified)
final_values = price_paths[:, -1] * stock_signals[:, -1]
sorted_paths = np.argsort(final_values)  # Worst to best

# Inspect worst performer
print_position_history(stock_signals, price_paths, sorted_paths[0], "stock")
```

---

### Next Steps

1. **Run `examples/analyze_strategy_positions.py`** to see the analysis in action
2. **Modify your TSLA command** to run programmatically (see Step 1 above)
3. **Inspect the signals** to understand what the strategy did wrong
4. **Adjust strategy parameters** based on what you find:
   - If over-trading → increase SMA periods (less signals)
   - If poor timing → adjust entry/exit thresholds
   - If positions too large → reduce `target_profit_usd`
