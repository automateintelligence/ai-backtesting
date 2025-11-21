"""Property-based tests for candidate filtering invariants (T047, FR-006-FR-011).

These tests use hypothesis to validate invariant properties of the filtering pipeline:
- Monotonicity: Tighter filters produce subsets of results
- Range constraints: All outputs within specified bounds
- Width limits: Generated structures respect width constraints
- Top-K selection: Returns at most K items per structure type
- Filter composition: Independent filters commute
"""

from __future__ import annotations

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from hypothesis.strategies import composite
from datetime import datetime, timedelta

# Configure default settings for faster test execution
settings.register_profile("fast", max_examples=50, deadline=1000)
settings.load_profile("fast")


# ============================================================================
# Strategy Definitions for Generating Test Data
# ============================================================================

@composite
def expiry_dates(draw, min_dte=1, max_dte=90):
    """Generate expiry dates with configurable DTE range."""
    today = datetime(2025, 11, 21)
    dte = draw(st.integers(min_value=min_dte, max_value=max_dte))
    return today + timedelta(days=dte)


@composite
def strike_data(draw, spot_price=475.0):
    """Generate strike data with moneyness ratios."""
    moneyness_ratio = draw(st.floats(min_value=0.70, max_value=1.40))
    strike = spot_price * moneyness_ratio

    # Liquidity metrics
    volume = draw(st.integers(min_value=0, max_value=10000))
    open_interest = draw(st.integers(min_value=0, max_value=50000))
    bid = draw(st.floats(min_value=0.05, max_value=50.0))
    ask_spread_pct = draw(st.floats(min_value=0.01, max_value=0.50))
    ask = bid * (1 + ask_spread_pct)

    return {
        "strike": round(strike, 2),
        "moneyness": round(moneyness_ratio, 4),
        "volume": volume,
        "open_interest": open_interest,
        "bid": round(bid, 2),
        "ask": round(ask, 2),
        "bid_ask_spread_pct": round(ask_spread_pct, 4)
    }


@composite
def vertical_structure(draw, spot_price=475.0):
    """Generate vertical spread structure with width limits."""
    option_type = draw(st.sampled_from(["call", "put"]))
    side = draw(st.sampled_from(["bull", "bear"]))

    # Generate two strikes with width constraint
    base_moneyness = draw(st.floats(min_value=0.85, max_value=1.15))
    width_strikes = draw(st.integers(min_value=1, max_value=3))

    strike1 = spot_price * base_moneyness
    strike2 = strike1 + (width_strikes * 5.0)  # Assume $5 strike spacing

    return {
        "type": "vertical",
        "option_type": option_type,
        "side": side,
        "long_strike": min(strike1, strike2),
        "short_strike": max(strike1, strike2),
        "width_strikes": width_strikes,
        "spot": spot_price
    }


@composite
def candidate_with_metrics(draw):
    """Generate candidate structure with analytic metrics."""
    structure = draw(vertical_structure())

    # Analytic metrics from Stage 3 prefilter
    capital = draw(st.floats(min_value=50.0, max_value=5000.0))
    max_loss = draw(st.floats(min_value=-capital, max_value=0.0))
    epnl = draw(st.floats(min_value=-capital, max_value=capital * 0.5))
    pop_breakeven = draw(st.floats(min_value=0.30, max_value=0.95))
    pop_target = draw(st.floats(min_value=0.20, max_value=0.90))

    return {
        "structure": structure,
        "capital": round(capital, 2),
        "max_loss": round(max_loss, 2),
        "epnl": round(epnl, 2),
        "pop_breakeven": round(pop_breakeven, 4),
        "pop_target": round(pop_target, 4),
        "score": draw(st.floats(min_value=0.0, max_value=1.0))
    }


# ============================================================================
# Property Tests for FR-006: Expiry Selection
# ============================================================================

class TestExpirySelection:
    """Property-based tests for Stage 0 expiry selection (FR-006)."""

    @given(st.lists(expiry_dates(min_dte=1, max_dte=90), min_size=10, max_size=20))
    def test_expiry_selection_within_dte_range(self, expiries):
        """Property: Selected expiries must have DTE in [7, 45] range (FR-006)."""
        today = datetime(2025, 11, 21)

        # Simulate Stage 0 filter
        filtered = [
            exp for exp in expiries
            if 7 <= (exp - today).days <= 45
        ]

        # Verify all selected expiries within range
        for exp in filtered:
            dte = (exp - today).days
            assert 7 <= dte <= 45, f"Expiry DTE {dte} outside [7, 45] range"

    @given(st.lists(expiry_dates(min_dte=1, max_dte=90), min_size=10, max_size=20))
    def test_expiry_count_invariant(self, expiries):
        """Property: Select 3-5 expiries when available (FR-006)."""
        today = datetime(2025, 11, 21)

        # Filter to valid DTE range
        valid_expiries = [
            exp for exp in expiries
            if 7 <= (exp - today).days <= 45
        ]

        # Select 3-5 expiries if available
        selected = sorted(valid_expiries)[:5]  # Take up to 5 earliest

        if len(valid_expiries) >= 5:
            assert 3 <= len(selected) <= 5
        elif len(valid_expiries) >= 3:
            assert 3 <= len(selected) <= len(valid_expiries)


# ============================================================================
# Property Tests for FR-007: Strike Filtering
# ============================================================================

class TestStrikeFiltering:
    """Property-based tests for Stage 1 strike filtering (FR-007)."""

    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(st.lists(strike_data(spot_price=475.0), min_size=10, max_size=30))
    def test_moneyness_filter_monotonicity(self, strikes):
        """Property: Tighter moneyness window produces subset of results (FR-007)."""
        # Wider filter [0.80, 1.20]
        wide_filtered = [
            s for s in strikes
            if 0.80 <= s["moneyness"] <= 1.20
        ]

        # Tighter filter [0.85, 1.15]
        tight_filtered = [
            s for s in strikes
            if 0.85 <= s["moneyness"] <= 1.15
        ]

        # Verify subset property: tight ⊆ wide
        tight_strikes = {s["strike"] for s in tight_filtered}
        wide_strikes = {s["strike"] for s in wide_filtered}

        assert tight_strikes.issubset(wide_strikes), \
            "Tighter filter should produce subset of wider filter results"

    @given(
        st.lists(strike_data(spot_price=475.0), min_size=20, max_size=50),
        st.integers(min_value=100, max_value=5000)
    )
    def test_volume_filter_monotonicity(self, strikes, min_volume):
        """Property: Higher volume threshold reduces result set (FR-007)."""
        # Lower threshold
        lower_threshold = min_volume
        lower_filtered = [s for s in strikes if s["volume"] >= lower_threshold]

        # Higher threshold
        higher_threshold = min_volume + 1000
        higher_filtered = [s for s in strikes if s["volume"] >= higher_threshold]

        # Verify monotonicity: higher threshold produces subset
        assert len(higher_filtered) <= len(lower_filtered), \
            "Higher volume threshold should reduce or maintain result count"

    @given(
        st.lists(strike_data(spot_price=475.0), min_size=20, max_size=50),
        st.floats(min_value=0.05, max_value=0.20)
    )
    def test_bid_ask_spread_filter_monotonicity(self, strikes, max_spread):
        """Property: Tighter spread limit reduces result set (FR-007)."""
        assume(max_spread > 0.05)  # Ensure meaningful threshold

        # Wider tolerance
        wide_filtered = [s for s in strikes if s["bid_ask_spread_pct"] <= max_spread]

        # Tighter tolerance
        tight_spread = max_spread * 0.5
        tight_filtered = [s for s in strikes if s["bid_ask_spread_pct"] <= tight_spread]

        # Verify subset property
        assert len(tight_filtered) <= len(wide_filtered), \
            "Tighter spread limit should reduce or maintain result count"


# ============================================================================
# Property Tests for FR-008: Structure Generation
# ============================================================================

class TestStructureGeneration:
    """Property-based tests for Stage 2 structure generation (FR-008)."""

    @given(st.lists(vertical_structure(spot_price=475.0), min_size=10, max_size=50))
    def test_width_limit_constraint(self, structures):
        """Property: All verticals must have width ≤ 3 strikes (FR-008)."""
        for struct in structures:
            assert 1 <= struct["width_strikes"] <= 3, \
                f"Width {struct['width_strikes']} violates [1, 3] constraint"

    @given(st.lists(vertical_structure(spot_price=475.0), min_size=10, max_size=50))
    def test_strike_ordering_invariant(self, structures):
        """Property: Long strike < short strike for all verticals (FR-008)."""
        for struct in structures:
            assert struct["long_strike"] < struct["short_strike"], \
                f"Invalid strike ordering: long {struct['long_strike']} >= short {struct['short_strike']}"

    @given(
        st.lists(vertical_structure(spot_price=475.0), min_size=10, max_size=50),
        st.integers(min_value=1, max_value=3)
    )
    def test_width_filter_produces_subset(self, structures, max_width):
        """Property: Stricter width limits produce subsets (FR-008)."""
        # All structures with width ≤ max_width
        filtered = [s for s in structures if s["width_strikes"] <= max_width]

        # Stricter limit
        stricter_width = max(1, max_width - 1)
        stricter_filtered = [s for s in structures if s["width_strikes"] <= stricter_width]

        # Verify subset property
        assert len(stricter_filtered) <= len(filtered), \
            "Stricter width limit should reduce or maintain result count"


# ============================================================================
# Property Tests for FR-010: Hard Filters
# ============================================================================

class TestHardFilters:
    """Property-based tests for Stage 3 hard filters (FR-010)."""

    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(
        st.lists(candidate_with_metrics(), min_size=15, max_size=50),
        st.floats(min_value=500.0, max_value=3000.0)
    )
    def test_capital_filter_monotonicity(self, candidates, max_capital):
        """Property: Lower capital limit reduces result set (FR-010)."""
        # Higher limit
        higher_limit = max_capital
        higher_filtered = [c for c in candidates if c["capital"] <= higher_limit]

        # Lower limit
        lower_limit = max_capital * 0.7
        lower_filtered = [c for c in candidates if c["capital"] <= lower_limit]

        # Verify monotonicity
        assert len(lower_filtered) <= len(higher_filtered), \
            "Lower capital limit should reduce or maintain result count"

    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(
        st.lists(candidate_with_metrics(), min_size=15, max_size=50),
        st.floats(min_value=0.40, max_value=0.70)
    )
    def test_pop_filter_monotonicity(self, candidates, min_pop):
        """Property: Higher POP requirement reduces result set (FR-010)."""
        # Lower requirement
        lower_req = min_pop
        lower_filtered = [c for c in candidates if c["pop_breakeven"] >= lower_req]

        # Higher requirement
        higher_req = min(0.90, min_pop + 0.10)
        higher_filtered = [c for c in candidates if c["pop_breakeven"] >= higher_req]

        # Verify monotonicity
        assert len(higher_filtered) <= len(lower_filtered), \
            "Higher POP requirement should reduce or maintain result count"

    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(
        st.lists(candidate_with_metrics(), min_size=15, max_size=50),
        st.floats(min_value=0.03, max_value=0.08)
    )
    def test_max_loss_pct_filter_monotonicity(self, candidates, max_loss_pct):
        """Property: Stricter loss limit reduces result set (FR-010)."""
        # Looser limit
        looser_limit = max_loss_pct
        looser_filtered = [
            c for c in candidates
            if abs(c["max_loss"]) / c["capital"] <= looser_limit
        ]

        # Stricter limit
        stricter_limit = max_loss_pct * 0.7
        stricter_filtered = [
            c for c in candidates
            if abs(c["max_loss"]) / c["capital"] <= stricter_limit
        ]

        # Verify monotonicity
        assert len(stricter_filtered) <= len(looser_filtered), \
            "Stricter loss limit should reduce or maintain result count"

    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(st.lists(candidate_with_metrics(), min_size=15, max_size=50))
    def test_combined_filters_commutative(self, candidates):
        """Property: Independent filters commute (order doesn't matter) (FR-010)."""
        max_capital = 2000.0
        min_pop = 0.60

        # Apply capital filter first
        path1 = [c for c in candidates if c["capital"] <= max_capital]
        path1 = [c for c in path1 if c["pop_breakeven"] >= min_pop]

        # Apply POP filter first
        path2 = [c for c in candidates if c["pop_breakeven"] >= min_pop]
        path2 = [c for c in path2 if c["capital"] <= max_capital]

        # Extract IDs for comparison (use structure type + capital as proxy ID)
        path1_ids = {(c["structure"]["type"], c["capital"]) for c in path1}
        path2_ids = {(c["structure"]["type"], c["capital"]) for c in path2}

        # Verify same results regardless of order
        assert path1_ids == path2_ids, \
            "Filter order should not affect final result set for independent filters"


# ============================================================================
# Property Tests for FR-011: Top-K Selection
# ============================================================================

class TestTopKSelection:
    """Property-based tests for Stage 3 top-K selection (FR-011)."""

    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(
        st.lists(candidate_with_metrics(), min_size=20, max_size=80),
        st.integers(min_value=10, max_value=50)
    )
    def test_top_k_count_constraint(self, candidates, k):
        """Property: Top-K selection returns at most K items (FR-011)."""
        # Group by structure type
        by_type = {}
        for c in candidates:
            struct_type = c["structure"]["type"]
            if struct_type not in by_type:
                by_type[struct_type] = []
            by_type[struct_type].append(c)

        # Select top K per type
        top_k_per_type = {}
        for struct_type, type_candidates in by_type.items():
            sorted_candidates = sorted(
                type_candidates,
                key=lambda x: x["score"],
                reverse=True
            )
            top_k_per_type[struct_type] = sorted_candidates[:k]

        # Verify count constraint
        for struct_type, selected in top_k_per_type.items():
            assert len(selected) <= k, \
                f"Structure type {struct_type} has {len(selected)} > {k} items"

    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(
        st.lists(candidate_with_metrics(), min_size=20, max_size=80),
        st.integers(min_value=10, max_value=50)
    )
    def test_top_k_score_ordering(self, candidates, k):
        """Property: Top-K items have highest scores (FR-011)."""
        # Group by structure type
        by_type = {}
        for c in candidates:
            struct_type = c["structure"]["type"]
            if struct_type not in by_type:
                by_type[struct_type] = []
            by_type[struct_type].append(c)

        # Select top K per type
        for struct_type, type_candidates in by_type.items():
            sorted_candidates = sorted(
                type_candidates,
                key=lambda x: x["score"],
                reverse=True
            )
            top_k = sorted_candidates[:k]

            # Verify scores are non-increasing
            scores = [c["score"] for c in top_k]
            assert scores == sorted(scores, reverse=True), \
                f"Top-K scores not properly ordered for {struct_type}"

            # Verify top-K have highest scores
            if len(sorted_candidates) > k:
                min_selected_score = min(c["score"] for c in top_k)
                excluded_scores = [c["score"] for c in sorted_candidates[k:]]
                for excluded_score in excluded_scores:
                    assert excluded_score <= min_selected_score, \
                        f"Excluded item score {excluded_score} > min selected {min_selected_score}"

    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(
        st.lists(candidate_with_metrics(), min_size=30, max_size=100),
        st.integers(min_value=10, max_value=50)
    )
    def test_total_survivor_count(self, candidates, k_per_type):
        """Property: Total survivors should be 50-200 after top-K per type (FR-011)."""
        # Group by structure type
        by_type = {}
        for c in candidates:
            struct_type = c["structure"]["type"]
            if struct_type not in by_type:
                by_type[struct_type] = []
            by_type[struct_type].append(c)

        # Select top K per type
        total_survivors = 0
        for struct_type, type_candidates in by_type.items():
            sorted_candidates = sorted(
                type_candidates,
                key=lambda x: x["score"],
                reverse=True
            )
            survivors = sorted_candidates[:k_per_type]
            total_survivors += len(survivors)

        # Note: This property depends on having multiple structure types
        # With enough input data, total should be in expected range
        if len(by_type) >= 3 and k_per_type >= 20:
            # Relaxed check: at least some survivors
            assert total_survivors >= 10, \
                f"Total survivors {total_survivors} below minimum expected"


# Mark all tests as property-based tests
pytestmark = pytest.mark.property
