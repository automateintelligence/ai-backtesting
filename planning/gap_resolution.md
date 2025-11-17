Based only on the spec.md, plan.md, and tasks.md and not any non-defined assumptions, explain to be in plain language how the software will operate:
1) How does the Monte Carlo simulation matrix get calculated and built for N=20 paths?
2) Given a ticker symbol, a) how, from where, and what period of the price history retrieved, b) how is a distribution fit to the price history?  What are the parameters of the fit that can be adjusted?
3) How do I define a strategy?  Would it be possible to use a ML model as part of a strategy?
4) Enumerate any gaps in design due to non-defined assumptions.
RESPONSE:
Based on my analysis of the specification documents, I can explain how the software operates in plain language:

  1) Monte Carlo Simulation Matrix (N=20 paths)

  How it's built:

  1. Historical Data Loading: The system loads historical OHLCV (Open, High, Low, Close, Volume) price data from a Parquet file
  cache, fetching from yfinance if not cached (FR-001, FR-085)
  2. Return Distribution Fitting:
    - Calculates log returns from closing prices
    - Fits a Laplace (double-exponential) distribution by default to these returns (FR-002)
    - The fitting process:
        - Checks for stationarity (non-stationary series rejected/transformed)
      - Uses MLE (Maximum Likelihood Estimation) or GMM (Generalized Method of Moments)
      - Records: estimator type, log-likelihood, AIC, BIC, convergence status
      - Validates parameters aren't "implausible" (e.g., scale > 0, finite values)
  3. Path Generation:
    - Uses the fitted distribution to randomly sample log returns: shape = [n_paths=20, n_steps=60]
    - Formula: log(S_t) = log(S_0) + cumsum(sampled_returns)
    - Converts back to prices: S_t = exp(log(S_t))
    - Result: 20 simulated price paths, each 60 steps long
  4. Storage Decision:
    - If 20 × 60 × 8 bytes × 1.1 < 25% of available RAM: keep in memory
    - Otherwise: use memory-mapped files (memmap) or compressed .npz format

  2) Price History Retrieval & Distribution Fitting

  a) How, from where, and what period:

  - From where: yfinance by default (Schwab API is optional/stub) - FR-001
  - How:
    - System checks local Parquet cache first (data/historical/{interval}/{symbol}.parquet)
    - If cache miss or stale (>1 day old for daily data): fetches from yfinance with 3 retry attempts
    - Supports incremental updates (appends new data to existing cache)
    - Detects corporate actions (splits/dividends) via >1% price divergence on overlapping bars - triggers full refresh
  - Period: User-configurable via CLI (start/end dates), typical default would be 5+ years for daily data

  b) Distribution fitting & adjustable parameters:

  Fit process (data-model.md lines 25-28):
  - Input: Array of log returns from closing prices
  - Minimum samples: 60 bars for Laplace/Student-T/Normal; 252 bars for GARCH-T (FR-032)
  - Preflight checks:
    - Stationarity test (non-stationary series rejected or transformed via differencing/detrending)
    - Autocorrelation/AR model detection

  Available models & parameters:
  1. Laplace (default): {loc: float, scale: float > 0}
  2. Student-T: {loc: float, scale: float > 0, df: int ∈ [2,100]}
  3. Normal: {mean: float, std: float > 0}
  4. GARCH-T (optional): GARCH volatility parameters + Student-T innovations

  Adjustable configuration (plan.md lines 12-19):
  - distribution_model: enum choice (laplace, student_t, normal, garch_t)
  - fit_window: number of historical bars to use (e.g., 252 for 1 year daily)
  - seed: random seed for reproducibility
  - Convergence limits, parameter bounds enforced automatically

  3) Defining Strategies & ML Model Integration

  Strategy definition (data-model.md lines 11-12, 71-100):

  A strategy is a Python class implementing the Strategy interface:

  class Strategy(ABC):
      def generate_signals(
          self,
          prices: pd.DataFrame,      # Price paths
          features: pd.DataFrame,    # Technical indicators, optional features
          params: Dict[str, Any]     # Strategy-specific parameters
      ) -> StrategySignals:
          # Returns: signals_stock, signals_option, option_spec, features_used

  Output format:
  - signals_stock: array of {-1, 0, 1} indicating short/flat/long positions
  - signals_option: array of {-1, 0, 1} for option positions
  - option_spec: strike, expiry, call/put, IV if using options
  - features_used: list of feature column names consumed

  ML model integration - YES, explicitly supported (FR-006, US3):
  - Features can be injected via pandas-ta indicators (SMA, RSI, Bollinger Bands, etc.)
  - Custom features can be added to the features DataFrame without modifying strategy engine code
  - The spec does NOT prohibit ML models - a strategy could:
    a. Accept trained model parameters in params dict
    b. Use features DataFrame as input to model.predict()
    c. Generate signals based on model output
    d. However: no explicit ML training/inference infrastructure is specified - you'd need to bring your own model

  4) Design Gaps Due to Non-Defined Assumptions

  Critical Gaps:

  1. Option Pricing IV Source (gap found):
    - Spec requires "per-strike implied volatility" (FR-016)
    - NOT DEFINED: Where IV comes from (historical volatility? IV surface API? user-provided?)
    - data-model.md line 61 mentions "warning when IV source missing" but no specification of IV retrieval method
  2. Strategy Signal Generation Logic:
    - Spec defines interface but not implementation of any concrete strategies
    - Only mentions "stock_basic" and "call_basic" in examples (data-model.md line 161-163)
    - Gap: No specification of default/example strategy logic (e.g., mean reversion thresholds, momentum signals)
  3. Feature Engineering Pipeline:
    - FR-006 mentions "technical indicators via pandas-ta"
    - Gap: No specification of:
        - Which indicators are pre-computed vs on-demand
      - How features are normalized/aligned across different timeframes
      - Feature storage schema in Parquet files
  4. Candidate Selector "Custom DSL" (FR-CAND-001):
    - Mentions "YAML-based boolean/threshold expressions"
    - Gap: No specification of DSL syntax, parser implementation, or validation rules
    - Only gap/volume spike selector is fully specified
  5. Conditional MC "Parametric Refit" (FR-CAND-005):
    - Spec requires "parametric state-conditioned return model"
    - Gap: No specification of:
        - How state features condition the distribution parameters
      - Whether this is a regression model, Bayesian update, or other method
      - Minimum sample size for state-conditioned fits
  6. Grid Objective Function Normalization (FR-083):
    - Formula: w1*mean_pnl + w2*sharpe + w3*(-drawdown) + w4*(-cvar)
    - States "each metric MUST be z-score normalized"
    - Gap: Z-score across what population? All configs in grid? Historical baseline? Undefined reference distribution
  7. Macro Series Alignment (FR-014):
    - Mentions "interpolation to bar frequency" with "3× bar interval" tolerance
    - Gap: Interpolation method not specified (linear? forward-fill? spline?)
  8. Replay Data Drift Handling (FR-019, FR-046):
    - Detects schema drift, row count changes, distribution shifts
    - Gap: No specification of how to resolve drift (reject? warn and proceed? auto-migrate?)
    - Only "refuse unless --allow_data_drift" is specified

  Minor Gaps (Reasonable Defaults Inferable):

  9. Slippage/Fees Model: StrategyParams includes fees and slippage fields but no specification of how they're applied
  (per-trade? percentage of notional? flat per contract?)
  10. Bankruptcy Path Handling: FR-050 says "abort with BankruptcyError" when all paths → 0, but doesn't specify partial
  bankruptcy (e.g., 5 of 20 paths bankrupt)
  11. Option Exercise Decision: No specification of early exercise logic for American options (spec assumes European via
  Black-Scholes)
  12. VPS Auto-Detection: ASSUME-001/002 require ≥20GB RAM and ≥4 cores, but no specification of behavior when running on smaller
   machines (abort? warn? clamp parameters?)

  Summary:

  The most critical gap is #1 (implied volatility sourcing) - option strategies cannot function without IV, yet the spec provides
   no retrieval mechanism. Gaps #2 and #4 (strategy implementations and custom DSL) would block US4 (screening) and conditional
  flows. The rest are implementation details that could be reasonably inferred or documented during development.
Clarifications:
1. Option Pricing IV Source (gap found) - Can we download IV from yfinance or Schwab or other along with pricing and other
  option greeks?
  2. Strategy Signal Generation Logic - Can we specify with a simple "hello world" SMA cross-over strategy to hold skeleton
  framework?
  3. Feature Engineering Pipeline - we will figure out which features we can download and from where once we get MVP working, and
  then we can determine which standard or custom features we will calculate.
  4. Candidate Selector "Custom DSL" (FR-CAND-001) - place-holder ""hello world" logic is fine for now.  We may employ LLMs to help
  use build the candidate selector criteria.
  5. Conditional MC "Parametric Refit" (FR-CAND-005) - What is your recommendation?
  6. Grid Objective Function Normalization (FR-083) - please perform web search for best practices on this topic.
  7. Macro Series Alignment (FR-014)  Well this depends on the macro feature doesn't it.  Some change gradually, in which case we
  would use a linear or spline or p-spline, but most macro features have discrete steps in time, like the Fed Rate, so we would
  just interpolate constant values on the finer timescale.
  8. Replay Data Drift Handling (FR-019, FR-046) - What is the best practice?
  9. Slippage/Fees Model - What is the best practice?
  10. Bankruptcy Path Handling - the whole point of multiple paths is to calculate stochastic likelihoods, so partial bankruptcies
  should absolutely be included.
  11. Option Exercise Decision - we should definitely allow early execution when a strategy indicates that the trading goals have
  been met before expiration.
  12. VPS Auto-Detection - not too worried about RAM, because the server RAM is already small, but auto-thread or -core detection
  would be prudent before parallel processing. 

Based on the research and your clarifications, here are my recommendations for each gap:

  1. Option Pricing IV Source ✅ RESOLVED

  Recommendation: Multi-source IV with fallback hierarchy

  # data/iv_source.py

  class IVSource:
      """Implied volatility data source with fallback chain."""

      def get_iv(self, symbol: str, expiry: date, strike: float) -> float:
          """
          Fallback order:
          1. yfinance options chain (has 'impliedVolatility' field)
          2. Historical volatility (realized vol over lookback window)
          3. User-provided constant (config default: 0.25)
          """
          try:
              # yfinance provides IV per contract
              ticker = yf.Ticker(symbol)
              chain = ticker.option_chain(expiry.strftime('%Y-%m-%d'))

              # Find closest strike
              df = chain.calls if is_call else chain.puts
              closest = df.iloc[(df['strike'] - strike).abs().argsort()[:1]]
              iv = closest['impliedVolatility'].values[0]

              if iv > 0 and iv < 5.0:  # Sanity check (0-500%)
                  log.info(f"Using yfinance IV: {iv:.2%} for {symbol}")
                  return iv
          except Exception as e:
              log.warning(f"yfinance IV fetch failed: {e}")

          # Fallback to historical vol
          log.warning(f"Using historical vol fallback for {symbol}")
          return self._calc_historical_vol(symbol, lookback=30)

      def _calc_historical_vol(self, symbol: str, lookback: int) -> float:
          """Annualized realized volatility."""
          prices = self.data_source.load_ohlcv(symbol, lookback)
          returns = np.log(prices['close'] / prices['close'].shift(1))
          return returns.std() * np.sqrt(252)

  Schwab API: Has options chains with Greeks/IV but requires OAuth approval. Defer to Phase 2.

  Specification update needed:
  FR-016-CLARIFICATION:
    iv_source_priority:
      1: yfinance options chain (contract-level IV)
      2: historical_volatility (30-day realized, annualized)
      3: config_default (0.25 or user-specified)

    validation:
      - iv > 0 and iv < 5.0 (sanity bounds)
      - log source used in run_meta.json
      - warn when using fallback

  ---
  2. Strategy Signal Generation - Hello World SMA Crossover ✅ RESOLVED

  Recommendation: Simple dual-SMA crossover as MVP baseline

  # strategies/sma_crossover.py

  from strategies.base import Strategy
  import pandas as pd
  import numpy as np

  class SMACrossoverStrategy(Strategy):
      """
      Hello World strategy: Long when fast SMA > slow SMA, flat otherwise.
      
      Params:
          fast_window: int (default 10)
          slow_window: int (default 30)
      """

      def generate_signals(
          self,
          prices: pd.DataFrame,  # columns: [close]
          features: pd.DataFrame,  # pre-computed or empty
          params: dict
      ) -> dict:
          """
          Returns:
              {
                  'signals_stock': np.ndarray[int8],  # {0, 1}
                  'signals_option': None,
                  'option_spec': None,
                  'features_used': ['sma_fast', 'sma_slow']
              }
          """
          fast = params.get('fast_window', 10)
          slow = params.get('slow_window', 30)

          # Compute SMAs
          close = prices['close'].values
          sma_fast = pd.Series(close).rolling(fast).mean().values
          sma_slow = pd.Series(close).rolling(slow).mean().values

          # Generate signals: 1 when fast > slow, 0 otherwise
          signals = np.where(sma_fast > sma_slow, 1, 0).astype(np.int8)

          return {
              'signals_stock': signals,
              'signals_option': None,
              'option_spec': None,
              'features_used': ['sma_fast', 'sma_slow'],
              'strategy_metadata': {
                  'fast_window': fast,
                  'slow_window': slow
              }
          }

  Spec addition:
  FR-006-EXAMPLE:
    default_strategies:
      - name: sma_crossover
        description: "Hello World baseline: dual SMA crossover"
        params: {fast_window: 10, slow_window: 30}
        type: stock_only

  ---
  3. Feature Engineering Pipeline ⏭️ DEFERRED

  Your decision: Figure out later after MVP. ✅ Agreed.

  Interim spec:
  FR-006-INTERIM:
    feature_sources:
      - pandas_ta indicators (optional)
      - user-provided Parquet files (data/features/{interval}/{symbol}_features.parquet)
      - strategies can request features via features_used list

    missing_feature_handling:
      - warn and skip if optional
      - error if required by strategy

  ---
  4. Candidate Selector Custom DSL ⏭️ PLACEHOLDER

  Your decision: Hello world placeholder, may use LLMs later. ✅ Agreed.

  Recommendation: Simple threshold-based placeholder

  # selectors/simple_selector.py

  class SimpleGapVolumeSelector(CandidateSelector):
      """Hello world selector: gap% and volume spike."""

      def select(self, features: pd.DataFrame, threshold: float) -> pd.Series:
          """
          Returns boolean Series where:
          - abs(open - prev_close) / prev_close > gap_threshold AND
          - volume / avg_volume_20d > volume_threshold
          """
          gap_pct = (features['open'] - features['close'].shift(1)) / features['close'].shift(1)
          vol_ratio = features['volume'] / features['volume'].rolling(20).mean()

          return (gap_pct.abs() > self.params['gap_threshold']) & \
                 (vol_ratio > self.params['volume_threshold'])

  Spec placeholder:
  FR-CAND-001-MVP:
    selectors:
      - gap_volume (default, implemented)
      - custom_dsl (placeholder for Phase 2, LLM-assisted)

  ---
  5. Conditional MC Parametric Refit 🎯 RECOMMENDATION NEEDED

  Recommendation: State-conditioned bootstrap (non-parametric) for MVP

  Given time constraints and your focus on transient conditions, I recommend:

  Phase 1 (MVP): Bootstrap resampling from similar historical episodes
  # models/conditional_mc.py

  def conditional_bootstrap_sampling(
      historical_returns: np.ndarray,
      state_features: np.ndarray,
      target_state: np.ndarray,
      distance_threshold: float = 2.0
  ) -> np.ndarray:
      """
      Sample returns from historical episodes similar to target state.
      
      Steps:
      1. Compute distances between target_state and all historical states
      2. Filter episodes within distance_threshold (Euclidean in z-score space)
      3. Bootstrap sample from filtered episodes
      4. Fallback to unconditional if <min_episodes
      """
      # Normalize features
      state_norm = (state_features - state_features.mean(axis=0)) / state_features.std(axis=0)
      target_norm = (target_state - state_features.mean(axis=0)) / state_features.std(axis=0)

      # Compute distances
      distances = np.linalg.norm(state_norm - target_norm, axis=1)
      similar_mask = distances < distance_threshold

      if similar_mask.sum() < 10:  # min_episodes
          log.warning("Insufficient similar episodes, falling back to unconditional")
          return historical_returns

      # Bootstrap from similar episodes
      similar_returns = historical_returns[similar_mask]
      return np.random.choice(similar_returns, size=(n_paths, n_steps), replace=True)

  Phase 2 (Optional): Parametric state-conditioned model
  - Fit mixture of distributions per state regime (e.g., Gaussian Mixture Model)
  - Or: regression from state features to distribution parameters (e.g., neural network)

  Spec update:
  FR-CAND-005-MVP:
    conditional_mc_methods:
      - bootstrap (default): resample from similar historical episodes
      - parametric (Phase 2): fit distribution conditional on state features

    fallback_order:
      1: bootstrap (if ≥10 similar episodes)
      2: unconditional MC (with warning)

    distance_metric: euclidean in z-score normalized feature space
    distance_threshold: 2.0 (configurable)

  ---
  6. Grid Objective Function Normalization ✅ RESEARCH COMPLETE

  Best practice: Z-score normalize across grid configs before weighting

  # optimizer/objective.py

  def compute_objective_scores(grid_results: List[dict]) -> np.ndarray:
      """
      Normalize metrics across grid, then apply weighted sum.
      
      Formula: objective = w1*z(mean_pnl) + w2*z(sharpe) + w3*z(-drawdown) + w4*z(-cvar)
      
      Where z(x) = (x - mean(x_grid)) / std(x_grid)
      """
      # Extract metrics
      mean_pnls = np.array([r['mean_pnl'] for r in grid_results])
      sharpes = np.array([r['sharpe'] for r in grid_results])
      drawdowns = np.array([r['max_drawdown'] for r in grid_results])
      cvars = np.array([r['cvar_95'] for r in grid_results])

      # Z-score normalize each metric across grid
      z_pnl = (mean_pnls - mean_pnls.mean()) / (mean_pnls.std() + 1e-8)
      z_sharpe = (sharpes - sharpes.mean()) / (sharpes.std() + 1e-8)
      z_dd = (-drawdowns - (-drawdowns).mean()) / (drawdowns.std() + 1e-8)  # Negative = better
      z_cvar = (-cvars - (-cvars).mean()) / (cvars.std() + 1e-8)

      # Weighted sum
      weights = config.get('objective_weights', {'w1': 0.3, 'w2': 0.3, 'w3': 0.2, 'w4': 0.2})
      objectives = (weights['w1'] * z_pnl +
                    weights['w2'] * z_sharpe +
                    weights['w3'] * z_dd +
                    weights['w4'] * z_cvar)

      return objectives

  Spec clarification:
  FR-083-CLARIFICATION:
    normalization: "Z-score (standardize) each metric across all grid configs"
    normalization_formula: "z(x) = (x - mean(x_grid)) / std(x_grid)"
    epsilon: 1e-8 (prevent division by zero)
    note: "Higher objective score = better config"

  ---
  7. Macro Series Alignment ✅ YOUR APPROACH APPROVED

  Your logic is sound: Gradual features (GDP growth) → spline; discrete steps (Fed Rate) → forward-fill constant.

  Recommendation: Alignment strategy metadata

  # data/macro_alignment.py

  ALIGNMENT_STRATEGIES = {
      'fed_rate': 'forward_fill',      # Discrete steps
      'unemployment': 'forward_fill',
      'gdp_growth': 'spline',          # Smooth interpolation
      'cpi_yoy': 'linear',
      'vix': 'linear'                   # Intraday variation
  }

  def align_macro_series(
      macro_df: pd.DataFrame,
      bar_index: pd.DatetimeIndex,
      strategy: str = 'forward_fill'
  ) -> pd.Series:
      """Align macro series to bar frequency."""
      if strategy == 'forward_fill':
          return macro_df.reindex(bar_index, method='ffill', limit=3)
      elif strategy == 'spline':
          return macro_df.reindex(bar_index).interpolate(method='spline', order=3)
      elif strategy == 'linear':
          return macro_df.reindex(bar_index).interpolate(method='linear')

  Spec update:
  FR-014-CLARIFICATION:
    alignment_strategies:
      forward_fill: "Discrete step features (Fed Rate, policy changes)"
      linear: "Gradually changing features with short gaps"
      spline: "Smooth features with long gaps (GDP, quarterly data)"

    strategy_selection:
      - per-feature configuration in config.yaml
      - default: forward_fill
      - max_gap_tolerance: 3× bar interval

  ---
  8. Replay Data Drift Handling ✅ RESEARCH COMPLETE

  Best practice: Detect → Warn → Block by default with override flag

  # replay/drift_detection.py

  def detect_drift(original_meta: dict, current_data: pd.DataFrame) -> dict:
      """
      Returns:
          {
              'drift_type': 'none|schema|distribution|count',
              'drift_severity': 'none|low|high',
              'can_replay': bool,
              'details': {...}
          }
      """
      drift_report = {'drift_type': 'none', 'drift_severity': 'none', 'can_replay': True}

      # 1. Schema drift (critical)
      if current_data.columns.tolist() != original_meta['schema']['columns']:
          drift_report.update({
              'drift_type': 'schema',
              'drift_severity': 'high',
              'can_replay': False,
              'details': {'column_diff': set(current_data.columns) ^ set(original_meta['schema']['columns'])}
          })
          return drift_report

      # 2. Row count drift
      row_pct_change = abs(len(current_data) - original_meta['row_count']) / original_meta['row_count']
      if row_pct_change > 0.05:  # >5%
          drift_report.update({
              'drift_type': 'count',
              'drift_severity': 'high' if row_pct_change > 0.10 else 'low',
              'can_replay': row_pct_change <= 0.10,  # Block if >10%
              'details': {'row_count_change_pct': row_pct_change}
          })

      # 3. Distribution drift
      current_returns = np.log(current_data['close'] / current_data['close'].shift(1)).dropna()
      mean_change = abs(current_returns.mean() - original_meta['return_mean']) / abs(original_meta['return_mean'])
      std_change = abs(current_returns.std() - original_meta['return_std']) / original_meta['return_std']

      if mean_change > 0.20 or std_change > 0.20:  # >20%
          drift_report.update({
              'drift_type': 'distribution',
              'drift_severity': 'high',
              'can_replay': False,
              'details': {'mean_change_pct': mean_change, 'std_change_pct': std_change}
          })

      return drift_report

  Spec update:
  FR-019-CLARIFICATION:
    drift_detection:
      schema_drift: "Column changes → BLOCK (severity: high)"
      count_drift: "Row count change >10% → BLOCK, 5-10% → WARN (severity: high/low)"
      distribution_drift: "Mean or std change >20% → BLOCK (severity: high)"

    replay_policy:
      - default: refuse replay if drift_severity='high'
      - override: --allow_data_drift flag bypasses block with warning
      - logging: record drift_report in replay run_meta.json

    versioning:
      - auto-version data: {provider}_{version}_{date}_{git_sha_8char}
      - example: yfinance_0.2.31_20251116_a3f5b2c

  ---
  9. Slippage/Fees Model ✅ RESEARCH COMPLETE

  Best practice: Tiered model with conservative estimates

  # engine/transaction_costs.py

  class TransactionCostModel:
      """
      Conservative slippage + fees model.
      
      Slippage models:
          - flat: Fixed percentage per trade
          - volume_adjusted: Scales with order_size / avg_daily_volume
          - bid_ask_spread: Use historical spread data (if available)
      """

      def __init__(self, config: dict):
          self.fee_per_contract = config.get('fee_per_contract', 0.65)  # Options: $0.65/contract
          self.fee_per_share = config.get('fee_per_share', 0.005)       # Stocks: $0.005/share
          self.slippage_model = config.get('slippage_model', 'flat')
          self.slippage_bps = config.get('slippage_bps', 5)             # 0.05% default (conservative)

      def apply_costs(
          self,
          position_change: float,  # Shares or contracts
          price: float,
          asset_type: str,  # 'stock' or 'option'
          avg_daily_volume: float = None
      ) -> float:
          """
          Returns total cost (fees + slippage) in dollars.
          Convention: cost > 0 reduces P&L
          """
          if position_change == 0:
              return 0.0

          notional = abs(position_change) * price

          # Fees
          if asset_type == 'stock':
              fees = abs(position_change) * self.fee_per_share
          else:  # option
              fees = abs(position_change) * self.fee_per_contract

          # Slippage
          if self.slippage_model == 'flat':
              slippage = notional * (self.slippage_bps / 10000)

          elif self.slippage_model == 'volume_adjusted':
              # Cap order at 5% of ADV, scale slippage non-linearly
              volume_ratio = abs(position_change) / (avg_daily_volume * 0.05)
              slippage_bps = self.slippage_bps * (1 + volume_ratio ** 2)  # Quadratic
              slippage = notional * (slippage_bps / 10000)

          return fees + slippage

  Spec update:
  FR-009-TRANSACTION-COSTS:
    slippage_models:
      flat: "Fixed percentage per trade (default: 0.05% = 5 bps)"
      volume_adjusted: "Scales quadratically with order_size / (0.05 * avg_daily_volume)"

    fees:
      stocks: "$0.005 per share (typical retail)"
      options: "$0.65 per contract (typical retail)"

    conservative_defaults:
      slippage_bps: 5  # Overestimate for safety
      max_order_pct_adv: 5  # Cap at 5% of average daily volume

    asset_specific:
      large_cap_stocks: "2-5 bps slippage"
      small_cap_stocks: "50-100 bps slippage (or skip in screening)"
      liquid_options: "10-20 bps slippage"
      illiquid_options: "50+ bps slippage"

  ---
  10. Bankruptcy Path Handling ✅ YOUR DECISION

  Your requirement: Include partial bankruptcies in metrics. ✅ Agreed.

  # metrics/risk_metrics.py

  def compute_bankruptcy_metrics(paths: np.ndarray) -> dict:
      """
      Track partial bankruptcies across MC paths.
      
      Returns:
          {
              'bankruptcy_count': int,
              'bankruptcy_rate': float,  # bankruptcies / n_paths
              'bankruptcy_timestamps': List[int],  # First zero crossing per path
              'non_bankrupt_paths': np.ndarray  # For conditional stats
          }
      """
      n_paths, n_steps = paths.shape

      # Find paths that hit zero
      bankrupt_mask = (paths <= 0).any(axis=1)
      bankruptcy_count = bankrupt_mask.sum()
      bankruptcy_rate = bankruptcy_count / n_paths

      # Find first zero crossing per bankrupt path
      bankruptcy_timestamps = []
      for path_idx in np.where(bankrupt_mask)[0]:
          first_zero = np.argmax(paths[path_idx] <= 0)
          bankruptcy_timestamps.append(first_zero)

      return {
          'bankruptcy_count': int(bankruptcy_count),
          'bankruptcy_rate': float(bankruptcy_rate),
          'bankruptcy_timestamps': bankruptcy_timestamps,
          'non_bankrupt_paths': paths[~bankrupt_mask],
          'severity': 'critical' if bankruptcy_rate > 0.05 else 'warning' if bankruptcy_rate > 0 else 'none'
      }

  Spec update:
  FR-050-CLARIFICATION:
    partial_bankruptcy_handling:
      - compute bankruptcy_rate = bankrupt_paths / n_paths
      - report in metrics: bankruptcy_count, bankruptcy_rate, first_crossing_times
      - compute conditional metrics on non-bankrupt paths
      - warn if bankruptcy_rate > 0% (any bankruptcies)
      - error if bankruptcy_rate > 5% (too risky)

    metrics_output:
      unconditional: "All paths"
      conditional_non_bankrupt: "Exclude bankrupt paths from mean/sharpe/etc"

  ---
  11. Option Exercise Decision ✅ YOUR REQUIREMENT

  Your requirement: Allow early exercise when strategy goals met. ✅ Agreed.

  Recommendation: Strategy-driven early exercise signals

  # strategies/base.py

  class Strategy(ABC):

      @abstractmethod
      def check_early_exercise(
          self,
          current_pnl: float,
          current_price: float,
          option_value: float,
          days_to_expiry: int,
          params: dict
      ) -> bool:
          """
          Strategy decides whether to exercise early.
          
          Examples:
              - Take profit if PnL > target
              - Stop loss if PnL < threshold
              - Exercise if ITM and near expiry
          """
          pass

  # Example implementation
  class TakeProfitStrategy(Strategy):
      def check_early_exercise(self, current_pnl, current_price, option_value, days_to_expiry, params):
          # Exercise if profit target hit
          profit_target = params.get('profit_target', 0.25)  # 25%
          return current_pnl / option_value > profit_target

  Spec update:
  FR-016-EARLY-EXERCISE:
    exercise_decision:
      - strategy-driven via check_early_exercise() method
      - called at each simulation step
      - returns: bool (exercise now) or None (hold until expiry)

    common_rules:
      take_profit: "Exercise if PnL > target_pct"
      stop_loss: "Exercise if PnL < -stop_loss_pct"
      expiry_threshold: "Auto-exercise if ITM and days_to_expiry < threshold"

    intrinsic_value_recovery:
      - on early exercise, realize intrinsic value: max(S - K, 0) for calls
      - log exercise timestamp and reason in run_meta

  ---
  12. VPS Auto-Detection ✅ YOUR REQUIREMENT

  Your requirement: Auto-detect CPU cores for parallel processing. ✅ Agreed.

  # config/system_detection.py

  import os
  import psutil

  def detect_system_resources() -> dict:
      """
      Auto-detect VPS resources and set safe defaults.
      
      Returns system_info dict for run_meta.json
      """
      cpu_count = os.cpu_count() or 1
      ram_gb = psutil.virtual_memory().total / (1024 ** 3)

      # Conservative defaults
      max_workers = max(1, min(cpu_count - 2, 6))  # Reserve 2 cores for OS, cap at 6

      # Memory thresholds
      mem_threshold_gb = ram_gb * 0.25  # In-memory if <25% RAM
      mem_abort_gb = ram_gb * 0.50      # Abort if ≥50% RAM

      system_info = {
          'os_type': os.name,
          'cpu_count': cpu_count,
          'ram_gb': round(ram_gb, 2),
          'max_workers_default': max_workers,
          'mem_threshold_gb': round(mem_threshold_gb, 2),
          'mem_abort_gb': round(mem_abort_gb, 2)
      }

      # Warnings
      if ram_gb < 20:
          log.warning(f"RAM ({ram_gb:.1f} GB) below recommended 20 GB. May hit memory limits.")

      if cpu_count < 4:
          log.warning(f"CPU count ({cpu_count}) below recommended 4+. Grid jobs will be slow.")

      return system_info

  Spec update:
  FR-018-AUTO-DETECTION:
    system_detection:
      - auto-detect: cpu_count, ram_gb, os_type at startup
      - set max_workers: max(1, min(cpu_count - 2, 6))
      - set mem_thresholds: 25% (in-memory), 50% (abort)
      - log detection results in run_meta.json

    warnings:
      - ram < 20 GB: "May hit memory limits"
      - cpu_count < 4: "Grid jobs will be slow"
      - os_type == 'Windows': "Unsupported OS" (per FR-068)

    user_override:
      - CLI flags override auto-detection
      - --max-workers, --mem-limit-gb

  # Gap Resolutions & MVP Clarifications

  ## Resolved Design Gaps

  1. ✅ IV Source: yfinance → historical vol → config default (0.25)
  2. ✅ Hello World Strategy: SMA crossover (10/30)
  3. ⏭️ Features: Deferred to post-MVP
  4. ⏭️ Custom DSL: Placeholder for Phase 2
  5. ✅ Conditional MC: Bootstrap resampling (non-parametric)
  6. ✅ Grid Normalization: Z-score across configs
  7. ✅ Macro Alignment: Forward-fill (discrete), spline (smooth)
  8. ✅ Data Drift: Detect → Block by default → Override flag
  9. ✅ Slippage/Fees: Flat 5 bps + $0.65/contract conservative
  10. ✅ Partial Bankruptcy: Track rate + conditional metrics
  11. ✅ Early Exercise: Strategy-driven check_early_exercise()
  12. ✅ Auto-Detection: CPU cores - 2, clamp at 6, mem 25%/50%