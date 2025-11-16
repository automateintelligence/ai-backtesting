# Implementation Plan: Backtesting & Strategy Spec Authoring (Quant Scenario Engine)

**Branch**: `001-mvp-pipeline`  
**Date**: 2025-11-16  
**Spec**: `specs/001-mvp-pipeline/spec.md` (authoritative)  
**Parents/Children**: Follows constitution; parent is spec.md, siblings include research.md, data-model.md, quickstart.md, contracts/, tasks.md.

## Summary
Build a CPU-only Quant Scenario Engine that loads Parquet OHLCV, fits heavy-tailed return models (Laplace default; Student-T/GARCH-T options), generates Monte Carlo paths, runs stock and option strategies, and emits reproducible artifacts. Support CLI commands `compare`, `grid`, `screen`, `conditional`, and `replay`, with deterministic seeding, resource-aware storage policy, and candidate-based backtesting/MC per spec FR-001..FR-040 and FR-CAND-001..006.

## Technical Context & Constraints
- **Runtime**: Python 3.11 on 8 vCPU / 24 GB RAM VPS; CPU-only.
- **Data**: Parquet canonical storage (DM-004..014), 1d/5m/1m bars; features stored separately. Default yfinance, Schwab stub optional; schema validation on load (FR-027), fingerprint + drift detection (FR-019, FR-028, DM-013).
- **MC**: Laplace default; Student-T/GARCH-T optional. Memory estimator (`n_paths*n_steps*8*1.1`) and storage policy thresholds per FR-013/FR-023; non-positive/overflow rejection per FR-022; implausible parameter bounds per FR-020/FR-037.
- **Pricing**: Black–Scholes default, swap-friendly (FR-016); option maturity/ATM edge handling per spec.
- **Config**: CLI > ENV > YAML precedence with defaults and incompatible-combo fail-fast (FR-009, FR-024, FR-025); component swap logging (FR-026).
- **Performance**: Budgets per FR-018 (≤10s baseline, ≤15m grid), throughput targets captured; resource limit enforcement + warnings/abort.
- **Observability**: Structured JSON logs, progress, diagnostics (FR-039, FR-040); run_meta immutability and atomic writes (FR-030).
- **Reproducibility**: Seeds applied everywhere (FR-012/021), capture package versions/system config/git SHA, data fingerprints (FR-019, FR-028, FR-034).
- **Assumptions**: Single-user execution, pre-downloaded Parquet, 8 vCPU/24 GB RAM (FR-018 context); revisit if violated.

## Workstreams
1) **Data & Schema**  
   - Implement DataSource adapters (yfinance default, Schwab stub) with retries and drift detection (FR-001, FR-017, FR-027, FR-028).  
   - Enforce missing-data tolerances and gap handling (FR-010, FR-029); align macro series (FR-014).  
   - Persist fingerprints and schema metadata in run_meta (FR-019, FR-034).

2) **MC Models & Storage Policy**  
   - Implement ReturnDistribution interface + Laplace/Student-T/GARCH-T fits with bounds, convergence limits, and implausible-parameter checks (FR-002, FR-020, FR-037).  
   - Log-return → price transform with overflow/non-positive rejection (FR-022).  
   - Memory estimator + policy: in-memory <25% RAM; memmap/npz ≥25%; abort ≥50% (FR-013, FR-023); record in run_meta.

3) **Strategies & Pricing**  
   - Stock/option strategy interfaces; option pricer abstraction with Black–Scholes default and plug-ins (FR-004, FR-016).  
   - Handle option-specific edge cases (maturity vs horizon, ATM precision, invalid IV) with structured errors (FR-022).

4) **CLI & Config**  
   - Typer CLIs for `compare`, `grid`, `screen`, `conditional`, `replay` with parameter validation against contracts (FR-005, FR-033).  
   - Config precedence (FR-024) and defaulting/incompatibility checks (FR-009, FR-025); audit component swaps (FR-026).  
   - Fail-fast + recoverable fallbacks logged per FR-038.

5) **Candidate Selection & Conditional Flows**  
   - CandidateSelector abstraction and default gap/volume rule (FR-CAND-001, -006).  
   - Episode construction `(symbol, t0, horizon, state_features)` (FR-CAND-002, FR-035); screening outputs per US4.  
   - Conditional backtest + conditional MC with bootstrap + parametric refit; fallback order logged (FR-CAND-004/005/036).  
   - Selector sparsity/zero-candidate and replay data-drift handling (FR-019, SC-011/012/020).

6) **Resource Limits, Observability, Reproducibility**  
   - Enforce time/memory budgets and worker caps (FR-018, FR-023).  
   - Structured logging + progress + diagnostics (FR-039/040); audit trail completeness.  
   - run_meta: seeds, versions (Python/pkg), git SHA, system config, data fingerprints, storage policy, fallbacks (FR-019, FR-021, FR-030, FR-034).

## Phases & Milestones
- **Phase 0: Architecture & Contracts**  
  - Finalize interfaces (ReturnDistribution, OptionPricer, CandidateSelector, RunConfig) and storage policy rules.  
  - Draft contracts/openapi for CLI/config schemas; update data-model.md and quickstart.md with resolved defaults.

- **Phase 1: Core Engine & CLI (compare)**  
  - Data adapters + schema validation + fingerprints.  
  - Laplace + Student-T fit/sample; MC engine with estimator/policy; stock vs option simulator; run_meta emission.  
  - `compare` CLI with config precedence, seed handling, artifacts (metrics JSON/CSV, run_meta).

- **Phase 2: Grids, Screening, Conditional**  
  - Grid runner with resource caps; progress + partial failure handling.  
  - Candidate selector + screening CLI; episode builder.  
  - Conditional backtest + conditional MC (bootstrap + parametric) with fallbacks; `replay` CLI enforcing drift checks.

- **Phase 3: Hardening & Edge Cases**  
  - Option-pricing edge handling, small/degenerate path cases, bankruptcy/zero-vol paths, max_workers boundaries, single-config grid.  
  - Performance validation vs budgets; observability/audit completeness; change/versioning hooks.

## Deliverables (Definition of Done)
- Updated `plan.md`, `data-model.md`, `quickstart.md`, `contracts/` aligning to spec; `tasks.md` with executable backlog.  
- Implemented CLIs (`compare`, `grid`, `screen`, `conditional`, `replay`) meeting FR-005/033 and US1–US8 acceptance scenarios.  
- MC + storage policy + option pricer per FR-002/013/016/020/022/023/037.  
- Candidate flows per FR-CAND-001..006; episode artifacts and conditional metrics per SC-010/011/012.  
- run_meta content: seeds, versions, git SHA, system config, data fingerprints, storage policy, fallbacks, drift status.  
- Tests: unit for distributions/pricers/config validation; integration for CLI commands; property/boundary tests for MC reproducibility and resource thresholds; coverage ≥80%.

## Risks & Mitigations
- **Performance budget miss**: profile MC and pricer hotspots; reduce paths/steps or swap pricer; ensure memmap fallback works.  
- **Data drift/quality**: strict schema checks, fingerprints, and drift blocking; clear warnings with override flag.  
- **Resource exhaustion**: preflight estimator + hard caps; partial results persisted for grids; fail-fast with structured errors.  
- **Reproducibility gaps**: capture full environment (git SHA, packages, system config) and seeds in run_meta; deterministic config precedence.  
- **Config complexity**: contracts as single source; defaults documented; conflicts rejected early.
