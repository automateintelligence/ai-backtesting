/superpowers:brainstorm "I have a new user story (US) for this project.  I want everything to remain modular because I have lots of different uses for this library and its capabilities.  My stated User Story 1 from 'specs/001-mvp-pipeline/spec.md' is to compare a stock trading strategy to an option trading strategy, assuming the same underlying and a given --stock-strategy and --option-strategy. The US1 stock-vs-option comparison already uses a concrete pricing model. The MarketSimulator (quant_scenario_engine/simulation/simulator.py (lines 10-90)) wires a BlackScholesPricer from quant_scenario_engine/pricing/black_scholes.py and, for every Monte Carlo path, reprices the option leg along that path to compute P&L/equity curves. So US1’s CLI compare command is evaluating stock signals directly on price paths while valuing the option strategy via closed-form Black–Scholes (European, CPU-friendly) with strike/IV/maturity pulled from OptionSpec. When you swap to a different pricer later (e.g., PyVollib), you’ll do it by supplying a different implementation of that same interface, but today the baseline Black–Scholes engine is what powers every option trade comparison.  

However for User Story 9 (US9), I would like to start with an assumption about the underlying stock like: 'neutral', 'strong-neutral', 'low-volatility', 'volatility-dir-uncertain', 'mild-bearish', 'strong-bearish', 'mild-bullish', 'strong-bullish' - all based on expected price movements and ranges of standard deviations or expected $ movement. i.e. 'strong-bullish' would be a move of >6% price change or 3 stddev, 'neutral' would be < 2% price change or 50% probability, 'volatility-dir-uncertain' would be +/- 3% price change or +/- 1 stddev.  This with inputs of its strike price, volume, volatility, basically everthing needed to price options.  Then run through a library of option trading strategies to optimize based on a --strategy-score.  I want to answer the question, "Given an underlying stock, a price direction assumption, and my option trade optimization constraints, in the universe of option spread positions, which one(s) are the best?"

I want you to help me define a fully modular, strategy-agnostic **option-trade scoring framework** that evaluates any option structure (single-leg, vertical, Back/Taio, Calendar, Diagonal, straddle, strangle, Collar, Butterfly, Condor, Iron Condor, Vertical Roll, Double Diagonal, Deep and Wide, etc.) under an assumed distribution of next-day price movements.

This is for **User Story 9 (US9)**, which differs from US1.
US1 compares stock-vs-option for a given strategy.
US9 instead scores and optimizes **option strategies alone**, given an assumption about the **next-day underlying price movement regime**.

### **1. Underlying-Movement Regime Assumptions (Input to US9)**

US9 begins with the user inputs providing a underlying stock pricing, technicals and fundamentals with a qualitative regime label for the expected next-day movement of the underlying stock.  We will focus on trading stocks with high volume, so we can make some assumptions about the liquidity of the options. These labels map to numerical distribution priors over return magnitude and direction:
- **neutral** → absolute move < 2% price or within ~0.5σ
- **strong-neutral** → absolute move < 1% or within ~0.25σ
- **low-volatility** → absolute move < 1% but narrower return distribution
- **volatility-dir-uncertain** → symmetric ±3% range or ±1σ
- **mild-bearish** → -2% to -4% center, skewed distribution
- **strong-bearish** → < -6% or >3σ downward
- **mild-bullish** → +2% to +4% center
- **strong-bullish** → > +6% or >3σ upward

These labels should be convertible into distribution parameters for **Monte Carlo simulation** (mean, σ, skew, kurtosis) OR selectable priors for ML-based return models.

### **2. Pricing Models (Pluggable Architecture)**

US9 must allow swapping pricing models. At a minimum, we want support for:
* **Black–Scholes** (baseline, European, CPU-efficient)
* **Bjerksund–Stensland** (recommended default for equity—American exercise, fast, closed-form approximation)
* **Heston** (stochastic volatility; calibrated to IV surface; pathwise simulation)
* **SLV / SVI local volatility surfaces** (future expansion; requires rich surface data)

Every pricer implements a shared interface:
* `price_option(underlying, strike, maturity, rate, dividend, iv_surface/state, type)`
* `greeks(…)`
* Must work inside both **entry scoring** and **intra-day repricing** for early exits.

### NOTE: Use a `trade_horizon` parameter (H) and treat it as a first-class concept that flows all the way from CLI → config → MC engine → scoring → early-exit logic.

The optimizer MUST accept a trade_horizon parameter (in trading days) which defines the intended holding period for a candidate trade.

For each candidate, the Monte Carlo engine SHALL simulate the underlying price process over trade_horizon days, and the option pricer SHALL evaluate leg values at the horizon, adjusting time-to-expiry and IV state accordingly.

All primary metrics (E[PnL], POP, ROC, VaR, CVaR, etc.) used in filtering and scoring for strategy-score intraday-spreads SHALL be computed over trade_horizon, and any dailyized metrics MUST clearly document the normalization applied.

- trade_horizon = 1 → intraday / next-day trade
- trade_horizon = 3 → 3-day income trade
- trade_horizon = 5 → 1-week-style hold
CLI / config
--trade-horizon 1 or --trade-horizon 3
Scenario / simulation config
The MC engine should take it as a core parameter:
steps = trade_horizon * bars_per_day 
Scoring configuration
The scoring function should know the horizon, because:
Thresholds like min E[PnL] and POP are horizon-dependent.
ROC can be reported as total and/or per day.
Early-exit logic with trade_horizon
For an open position at time t_now:
Remaining horizon: H_remaining = max(1, H_total - days_elapsed)
Run MC paths from “now” out to H_remaining.
Compute PnL_Hremaining, POP, tail risk.

### **3. Monte Carlo Expectations (Core of US9 Scoring)**

For each option strategy candidate, US9 must estimate:
* Expected one-day P&L:
  `E[PnL_H]` computed by repricing the position across simulated paths.
* Probability of profit (break-even POP):
  `POP_0 = P(PnL_H ≥ 0)`
* Probability of hitting a profit target:
  `POP_target = P(PnL_H ≥ profit_target)` (default profit_target = +$500) “I want $500–1000 over the whole trade, whether it’s 1 day or 3 days.”
* Return on capital (ROC):
  `ROC_H = E[PnL_H] / capital_used`
* Tail-risk / worst-case measures:
  * `MaxLoss_trade`
  * `VaR_5%`
  * `CVaR_5%`

## US9 should allow swapping among these engines:
Monte Carlo distributions can come from:
1. **GARCH-t (baseline volatility-clustered, heavy-tailed model), Student-t (fast - seems to be a good fit for NVDA and AAPL), or Laplacian** best fit from distribution_audit.py
2. **Regime-conditioned bootstrap** (nonparametric resampling of historical bars matching current regime)
  **Idea:** Let the data speak, but condition on regime features.
  - Take a window (e.g., last 1–3 years) of high-frequency returns.
  - Tag each bar with **features**:
    - Volatility state (e.g., ATR or realized vol quintile)
    - Trend state (SMA slope, MACD)
    - Macro/market regime (VIX level, broad-market score from your study)
  - When you need the next-day distribution:
    - Find historical bars with **similar regime features** to “now.”
    - Bootstrap sequences of returns from those segments to create Monte Carlo paths.
3. **ML conditional distribution model** (e.g., gradient-boosted quantile model predicting next-day return quantiles)
  - Use a **gradient boosted trees model** (e.g., XGBoost/LightGBM) or **quantile random forest** to predict:
  - Conditional **distribution of next-day return**, via **quantile regression** (e.g., 5%, 50%, 95% quantiles), or
  - Directly predict parameters of a parametric distribution (e.g., mean/vol/ν of a Student-t).
  - Features (the most powerful part of using ML):
    - Recent realized vol, ATR, SMAs, RSI, MACD, gaps, volume z-scores
    - Market-wide factors (SPY return, VIX, your BroadMarketScore)
    - Time of month/quarter, etc.
  - Then:
    - Sample from the learned conditional distribution to generate MC paths.
    - Or use predicted quantiles directly to approximate VaR and tail behavior.

### **4. Trade Representation & Repricing Logic**

A position is stateful:
* Each leg has: side, type, strike, expiry, quantity, **fill_price**.
* P&L must always be computed relative to *actual fills*, not model marks.

Repricing must recompute:
* current Greeks
* current theoretical values
* updated next-day distribution conditioned on today
* full pathwise P&L distribution for early-exit analysis

### **5. Hard Filters (Reject Before Scoring)**

Before computing the composite score, reject any candidate trade that violates:
* `capital_used > 15000`
* `MaxLoss_trade / capital_used > 0.05`
* `E[PnL_H] < 500`
* `POP_0 < 0.60`
* `POP_target < 0.30` (probability of hitting $500+)

### **6. Composite Strategy Score (intraday-spreads)**

US9 uses a composite weighted score to rank candidate option structures.
This model includes POP, ROC, risk, and Greeks.

Normalized components:
* `POP_norm` in [0,1]
* `ROC_norm` in [0,1]
* `TailPenalty = (MaxLoss_trade / 0.05)`
* `DeltaPenalty = |Delta - Delta_target| / Delta_scale`
* `ThetaReward` = positive value for Theta>0, maxing at 1
* `GammaPenalty = |Gamma| / Gamma_scale`
* `VegaPenalty = |Vega| / Vega_scale`

For a *directional* spread variant, you’d change `DeltaPenalty` to reward |Δ| in the desired direction instead of penalizing it.

Final score:
```
Score_intraday_spreads =
    w_pop   * POP_norm +
    w_roc   * ROC_norm +
    w_theta * ThetaReward
  - w_tail  * TailPenalty
  - w_delta * DeltaPenalty
  - w_gamma * GammaPenalty
  - w_vega  * VegaPenalty
```

Default weights reflecting business priorities:
* w_pop = 0.35
* w_roc = 0.30
* w_tail = 0.15
* w_theta = 0.10
* w_delta = 0.05
* w_gamma = 0.03
* w_vega = 0.02

# **Delta (Δ)**: how much the position’s price changes for a $1 move in the underlying.
  * For neutral income spreads, you want Δ near 0.
  * For directional spreads, you want Δ ~ 0.3–0.6 in your trade direction.
# **Theta (Θ)**: daily time decay.
  * For income trades, **you want Θ > 0**, ideally reasonably large relative to capital.
  * So **ThetaReward** in the score makes sense.
# **Gamma (Γ)**: how quickly delta changes as price moves.
  * High gamma means your Δ can swing rapidly and P&L becomes very path-dependent.
  * For intraday income spreads, you generally **want modest gamma**, so a small penalty is appropriate.
# **Vega (V)**: sensitivity to implied volatility.
  * For short premium spreads, you’re short vega; IV spikes hurt.
  * You may want to penalize large |V| for stability.

US9’s optimizer should compute:
* Spread Candidates
* The multi-stage scoring result
* A diagnostic bundle (why the score is what it is)
* A ranking across all candidate strategies

### **7. Options Spread Candidate Selection**
full brute force over *every* strike / expiry / structure is usually overkill, but you also don’t need anything exotic. A **2-stage search** with a **smart candidate generator** gets you 90% of the value with tractable compute.

## 1. How big is the search space, roughly?

Let’s say for one underlying, on a “typical” equity options chain:
* 8–12 strikes ITM + 8–12 strikes OTM that are realistically tradeable
* 3–6 expirations you might consider (short-dated weeklies + maybe 1–2 monthlies)
* A few structure templates:
  * Single-leg calls/puts
  * Vertical spreads (debit/credit)
  * Iron condors
  * Strangles/straddles

If we **don’t constrain anything**, vertical spreads alone blow up:
* Let `S` = number of candidate strikes per expiry (say 15)
* For each expiry, choose strike pairs (i, j) with i < j
* That’s `S * (S – 1) / 2 ≈ 105` spreads *per side* (call / put) *per expiry*
* With 4 expiries: `105 * 2 * 4 ≈ 840` verticals

Add iron condors:
* Roughly (call spread choices) × (put spread choices); this can easily reach low **thousands** of combinations for one underlying and a handful of expiries.

Now multiply by:
* Different **widths** (1-strike wide, 2-strike wide, etc.)
* Different **credit/debit constraints**

So you’re quickly in the **1,000–10,000 candidate** range.

Is that catastrophic?

* For a **lightweight analytic pricer** (Black–Scholes/Bjerksund–Stensland) and a **cheap approximate POP/ROC**, 1–5k candidates is fine.
* For **full Monte Carlo + intraday-spreads scoring** with 5k–10k paths per candidate, you don’t want to do that on *every* structure.

Hence: staged search.

---

## 2. Stage 0 – Choose expirations intelligently

You don’t need the whole calendar. For intraday spreads:
* Focus on **short DTE**: say **7–45 days** to start.

  * Very short (0–2 DTE) is special; I’d treat those as a separate mode.
* Pick **3–5 expiries**:
  * Nearest weekly
  * Next 1–2 weeklies
  * Maybe 1 monthly out

Rules of thumb:
* **Income spreads:** 14–45 DTE often sensible (good theta, not insane gamma).
* **Very short DTE gamma plays:** handle separately, smaller candidate set and more conservative risk budgets.

So Stage 0 narrows the expiries to a small list `E ≈ 3–5`.

---

## 3. Stage 1 – Restrict strikes using moneyness & liquidity

Given your regime label (neutral, strong-bullish, etc.), we can define a **strike window**:
* For **strong-bullish**:
  * Focus on **OTM calls** (e.g. +0% to +20% above spot) and **ITM puts** if doing bullish put spreads.
* For **neutral / income**:
  * Focus on **short OTM options**: maybe ±5–15% around spot.
  * Exclude deep OTM junk with no volume.

Practical filters per expiry:
1. **Moneyness window** (relative to underlying ( S_0 )):
   * Only consider strikes `K` such that:
     * `K/S_0 ∈ [0.85, 1.15]` for regular spreads, or narrower depending on regime.
2. **Liquidity filters**:
   * `volume >= min_volume` (e.g., 100 or 500 contracts)
   * `open_interest >= min_OI`
   * `bid-ask_spread <= max_spread` relative to price (e.g., < 10–15% of mid)

This generally reduces each expiry to maybe **8–12 usable strikes** for calls and puts.

Call that `S_eff`; realistically `S_eff ≈ 8–12`.

---

## 4. Stage 2 – Generate canonical structures with width limits
Now define **structure templates** and **width constraints**.

### 4.1 Vertical spreads

For each expiry and side (call/put):
* Only allow widths up to W strikes (e.g. 1–4 strikes ≈ a few dollars to tens of dollars wide).
* Only allow **short leg** within the “core” moneyness band; wings can go a bit further.

Then verticals per expiry are roughly:
* `~S_eff * W` per side instead of `S_eff^2`.
  * Example: `S_eff = 10`, `W = 3`, then ≈ `10 * 3 = 30` per side.
* For 4 expiries and both call/put: `30 * 2 * 4 = 240` verticals.

### 4.2 Iron condors

Build iron condors by pairing:
* A short call spread around upper band
* A short put spread around lower band

Again, with width limits and banded strikes, you’re probably talking **a few hundred** condors, not thousands.

### 4.3 Straddles/strangles

These are single-strike (ATM) or simple OTM pairs. Candidate count is tiny (dozens).

---

## 5. Stage 3 – Cheap prefilter scoring (no MC yet)

This is where you answer “Is it unrealistic to run them all?”
No, if you **don’t** run full Monte Carlo on all of them. Instead:
1. For each candidate:
   * Use **analytic pricer** (Black–Scholes or Bjerksund–Stensland).
   * Use a **simple underlying distribution** approximation:
     * Normal or Student-t with mean/σ consistent with the regime label, *not yet* GARCH-t / ML.
   * Approximate:
     * Capital (`C`)
     * MaxLoss (defined by structure)
     * POP_approx (from closed-form or delta-based approximation)
     * ROC_approx (`E[PnL_approx] / C`)

2. Apply **hard filters early**:
   * `C <= 15000`
   * `MaxLoss / C <= 0.05`
   * `E[PnL_approx] >= 500`
   * `POP_approx >= POP_min` (e.g., 0.6 for break-even)

3. Keep **only the top K candidates per structure type** based on:
   * A simplified version of your `intraday-spreads` score (POP + ROC – TailPenalty), ignoring detailed Greeks for now.
K doesn’t need to be huge. For one underlying:
* K=20–50 per structure type is usually enough.
* With 3–4 structure types, you end up with maybe **50–150 survivors**.
Running full MC on ~100–200 candidates is completely reasonable on your CPU VPS.

---

## 6. Stage 4 – Full intraday-spreads scoring with MC and rich pricers

For the survivors:
1. Swap to your **best available pricing model**:
   * Bjerksund–Stensland as default
   * Heston or SLV in “high realism” mode if IV surface and calibration are available.

2. Use your **preferred underlying distribution engine**:
   * GARCH-t baseline
   * Regime-conditional bootstrap
   * ML conditional distribution

3. Simulate paths and compute:
   * `E[PnL_H]`
   * `POP_0`, `POP_target (≥500)`
   * `ROC_H`
   * Tail metrics: VaR, CVaR, MaxLoss scenario confirmation
   * Full Greeks for the position at entry

4. Apply your **final composite score**:
   `Score_intraday_spreads = POP + ROC + Theta – penalties (tail, delta, gamma, vega)`

5. Rank and present the **top N** trades with diagnostics.
So we do **broad, cheap sweep → narrow, expensive refinement**.

---

## 7. Is it realistic to “run them all”?

Putting the numbers together:
* Raw candidates after strike/expiry/liquidity filters: **hundreds to low thousands**.
* Cheap prefilter scoring: trivial; a few thousand analytic valuations per underlying is fine.
* Survivors for full MC: **50–200** trades.

For MC:
* Example: 200 candidates × 5,000 paths × (say) 60 time steps
  * That’s 60M pricer evaluations, but:
    * Underlying can be vectorized.
    * Many pricers are analytic or semi-analytic.
    * You can slash paths to 1,000–2,000 for initial tests and go higher only on the top 10–20 trades.

If you structure it well (NumPy/JAX/vectorized loops or C++ backend), this is realistic on an 8-core VPS, especially if you’re not trying to do this on 100 underlyings at once.

If you *do* want to scale to many underlyings in one sweep, you’d probably:
* Limit each to **fewer expiries**
* Smaller K per structure type
* Possibly stagger MC runs or use a job queue.

---

## 8. High-level rule set you can encode

You can literally codify a candidate generation policy like:
1. **Expiries:**
   * Choose 3–5 expiries with DTE in [7, 45].

2. **Strikes per expiry (for this regime):**
   * Keep only strikes with:
     * `K/S0 is in the range of regime-specific band` (e.g. [0.9, 1.1])
     * `volume >= 100`, `open_interest >= 100`, `bid-ask <= 15% of mid`.

3. **Structures:**
   * Per expiry, generate:
     * Verticals: width 1–3 strikes
     * Iron condors within ±10–15% around spot
     * Straddles/strangles at ATM ± small OTM.

4. **Prefilter scoring:**
   * Use analytic pricer + simple distribution.
   * Apply capital/max-loss/E[PnL]/POP filters.
   * Keep top K per structure type.

5. **Final scoring:**
   * Use GARCH-t / ML MC + Bjerksund (or Heston/SLV).
   * Compute full `intraday-spreads` score.
   * Rank & return.

### **8. Deliverable for US9**

Given:
* An underlying-movement type like “strong-bullish”
* A full option chain with strikes, expiries, IVs
* The user-selected `--strategy-score intraday-spreads`
* Access to one of the pricing engines
* The Monte Carlo distribution model

US9 must:
1. Generate candidate option structures (verticals, calendars, strangles, etc.)
2. Compute all metrics (POP, ROC, Greeks, tail risk)
3. Apply filters
4. Score each candidate
5. Return a ranked list with explanations and diagnostics
6. Support the same process for **repricing an open position intraday**
7. Use one config.yml file for all parameter selections (stock and option pricing models to be used, spread types to be explored, # strike prices, # expirations, trade horizon, profit_target, etc.)

Generate:
Before we build the **complete spec** for US9 (SDD-ready) in specs/spec.md, do you have anything to add?
"

Generate:
* The **complete spec** for US9 (SDD-ready) in specs/spec.md
* A **unified StrategyScore interface** to plug into any strategy
* Or the **English-to-code prompt template** for superpowers to generate the implementation.
"
