# Research Findings

## Decision Log

1) **Option pricer backend for MVP and extension**  
**Decision:** Use closed-form Black–Scholes (from scipy/numpy) for European calls/puts with fixed IV; design an `OptionPricer` interface with a pluggable backend and ship a lightweight optional adapter using `py_vollib` for more accurate greeks/IV handling. Defer QuantLib/Heston to a follow-on adapter behind the same interface.  
**Rationale:** BS analytic keeps CPU-only VPS fast, minimizes heavy deps/compile, and matches MVP acceptance. An interface now prevents lock-in and allows swapping pricers via config. `py_vollib` is pure-Python bindings and easy to toggle for users who want better greeks without the weight of QuantLib.  
**Alternatives considered:** Direct QuantLib/Heston integration now (heavier install, longer compile, overkill for MVP); custom Heston implementation (complex, low ROI for v1); staying BS-only without an interface (blocks future swaps, violates modifiability goal).

2) **Return distribution fitting approach**  
**Decision:** Default to Laplace fit via `scipy.stats.laplace` on log returns; enable Student-T via `scipy.stats.t`; optionally enable GARCH-T via `arch` when `use_garch` flag is set. Persist fitted params + seed in run metadata.  
**Rationale:** Laplace covers fat-tails with minimal tuning and is fast. Student-T offers heavier tails for stress. GARCH-T is available but off-by-default to keep runtime under 10s and avoid overfitting small samples. Persisting params + seeds satisfies reproducibility requirements.  
**Alternatives considered:** Normal-only (insufficient fat-tail coverage); always-on GARCH (too slow for 1k×60 baseline); mixture models (higher complexity, not needed for MVP tests).

3) **Conditional candidate episode generation & Monte Carlo conditioning**  
**Decision:** Build a deterministic `CandidateSelector` DSL that emits episodes based on filter rules (gap/volume/volatility). For conditional MC, start with non-parametric return bootstrapping from matched episodes plus optional parametric refit (Laplace/Student-T) on that subset; fall back to unconditional fit when candidate pool < N_min.  
**Rationale:** Rule-based selectors match spec acceptance, are explainable, and run fast over ≥100 symbols. Bootstrapping conditioned on matched episodes gives scenario realism without heavy modeling; parametric refit preserves speed. Fallback avoids empty pools.  
**Alternatives considered:** kNN state embedding or ML classifiers (higher complexity, slower); pure unconditional MC (ignores conditioning goal); full Copula models (overkill for MVP scope).

4) **Historical data sourcing & partitioning**  
**Decision:** Use yfinance as default loader; stub Schwab adapter with identical interface and allow config switching. Store OHLCV/features as Parquet partitioned by `symbol=` and `interval=` with versioned filenames when sources change.  
**Rationale:** yfinance is easy and fast to prototype; a stub keeps contract stable for future Schwab integration. Partitioned Parquet matches DNFR requirements and speeds slicing for candidate scans. Versioned files avoid schema drift surprises.  
**Alternatives considered:** CSV-only (slower, no schema enforcement); wiring Schwab first (blocked while testing credentials; slows MVP); shared DB (unneeded for single-user VPS).

5) **Monte Carlo performance & storage policy**  
**Decision:** Generate MC paths in-memory when estimated footprint <25% RAM; switch to chunked generation + `numpy.memmap` when ≥25% and `.npz` persistence only when reuse/replay requested. Use vectorized ops + optional `numba` JIT; cap workers to ≤6 on 8 vCPU.  
**Rationale:** Aligns with DM-008..DM-014 and resource limits; memmap prevents OOM while keeping CPU-friendly. Numba speeds path generation without GPU. Worker cap matches FR-018.  
**Alternatives considered:** Always persist MC (wastes disk, slower); Dask/Ray (heavier orchestration for current scope); GPU acceleration (unavailable on target VPS).
