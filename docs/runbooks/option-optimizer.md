# Option Strategy Optimizer Runbook

## Runtime Modes
- **Full sweep (mode a)**: Broad candidate search may run up to 1 hour (FR-061). Use during pre/post-market with after-hours data.
- **Retest (mode b)**: Re-evaluate cached Top-10 with refreshed market data in <30 seconds (FR-061). Use the `--retest top10.json` flow.
- **Batch retest**: 10 cached Top-10 lists in ~5 minutes (<30s per ticker) for SC-012. Schedule full sweeps separately.

## Data Sources
- Default: `--data-source schwab` (Trader API). Emits warning and falls back to yfinance when unavailable.
- Capture provider provenance in logs and results; avoid parallel hammering of Schwab (see docs/data-sources/parallel-runbook.md).

## Commands
- Full sweep example:
```bash
qse optimize-strategy --ticker NVDA --regime strong-bullish --trade-horizon 3 \
  --config config.yml --data-source schwab --override "mc.num_paths=5000"
```
- Retest cached list:
```bash
qse optimize-strategy --ticker NVDA --regime strong-bullish --trade-horizon 1 \
  --config config.yml --data-source schwab --retest top10.json
```
- Monitor position:
```bash
qse monitor --position my_trade.json --interval 300 --data-source schwab
```

## Performance Tips
- Use default 5k paths; adaptive CI will raise paths only when CI is wide (FR-032/FR-033).
- Limit expiries/structures via config for faster sweeps; retest mode skips Stage 0–3.
- Parallelize [P] tasks judiciously; avoid overlapping file edits.

## Verification
- Tests: `pytest -q tests/unit/optimizers` (targeted); full suite may take longer.
- Lint: `ruff check .`
- Artifacts: save Top-10/Top-100, diagnostics (stage counts, rejection breakdown), and orders JSON.

## Quality Gate (Constitution Principle XIX, FR-076-FR-081)

### Coverage Requirements
Per Constitution Section II.XV (Testing Discipline) and specification FR-076-FR-081:

- **Line Coverage**: ≥80% across `qse/{optimizers,pricing,distributions,scorers}` modules
- **Branch Coverage**: 100% for critical paths (Stage 0-4 pipeline, MC scoring, composite scoring)
- **Test Runtime**: Full test suite must complete in <2 minutes for fast feedback loops (FR-079)

### Running Tests with Coverage Enforcement

```bash
# Run full test suite with coverage gate (fails if <80%)
pytest

# Run specific test categories
pytest tests/unit/          # Unit tests (<30s target)
pytest tests/integration/   # Integration tests (<60s target)
pytest tests/property/      # Property-based tests (<20s target)
pytest tests/contract/      # Contract tests (<5s target)

# Generate detailed coverage report
pytest --cov-report=html
# View report at htmlcov/index.html

# Check coverage for specific modules
pytest --cov=qse.optimizers --cov-report=term-missing
pytest --cov=qse.pricing --cov-report=term-missing
pytest --cov=qse.distributions --cov-report=term-missing
pytest --cov=qse.scorers --cov-report=term-missing
```

### Test Categories and Coverage Targets

1. **Unit Tests** (≥80% line coverage, <30s runtime)
   - Isolated component testing for OptionPricer implementations, ReturnDistribution generators, StrategyScorer plugins
   - Stage 1-3 filters (moneyness, liquidity, analytic prefiltering)

2. **Integration Tests** (<60s runtime)
   - Stage 0→4 pipeline validation
   - Regime→distribution→pricing→scoring flow
   - Cost modeling integration

3. **Property-Based Tests** (<20s runtime, FR-047)
   - Candidate filtering invariants (monotonicity, width limits)
   - Uses `hypothesis` library for invariant validation

4. **Contract Tests** (<5s runtime, FR-045)
   - MCP protocol compliance against `contracts/openapi_009.yaml`
   - Response schema validation for optimize-strategy and monitor commands

5. **Resilience Tests** (FR-046, Edge Cases)
   - Schwab outage/fallback scenarios (FR-005)
   - Pricer convergence failures (FR-021, FR-022)
   - Resource limits and timeout handling (FR-081)

### Quality Gate Enforcement

The quality gate is enforced via `pytest.ini` configuration:

```ini
[pytest]
addopts = --cov=quant_scenario_engine --cov-report=term-missing --cov-fail-under=80
```

**Failures**: If coverage drops below 80%, pytest will exit with non-zero status, blocking CI/CD pipelines and merges.

### Pre-Commit Checklist

Before committing Phase 12 work:

1. ✅ All tests pass: `pytest`
2. ✅ Coverage ≥80%: Verified by pytest exit code
3. ✅ Lint clean: `ruff check .`
4. ✅ Test runtime <2min: Monitor pytest duration output
5. ✅ Critical paths 100% branch coverage: Manual review of Stage 0-4, MC scoring, composite scoring modules

### Troubleshooting Coverage Issues

**Coverage below 80%:**
- Identify uncovered lines: `pytest --cov-report=term-missing`
- Focus on critical paths first (Stage 0-4, pricing, scoring)
- Add targeted unit tests for missing branches

**Slow tests (>2min):**
- Use `pytest --durations=10` to identify slowest tests
- Reduce hypothesis `max_examples` if property tests are slow
- Check for inefficient test data generation

**Contract test failures:**
- Validate against `specs/009-option-optimizer/contracts/openapi_009.yaml`
- Ensure response schemas match specification exactly

### CI/CD Integration (Future)

When CI/CD is configured:
- Enforce coverage gate on all PRs
- Fail builds if coverage drops below threshold
- Generate coverage reports and upload to coverage tracking service
- Run full test suite on every push to feature branches
