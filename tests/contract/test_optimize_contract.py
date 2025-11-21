"""Contract tests for optimize-strategy command against openapi_009.yaml (T045, FR-048-FR-055)."""

from __future__ import annotations

import pytest
import yaml
from pathlib import Path


def load_openapi_spec() -> dict:
    """Load OpenAPI contract specification."""
    contract_path = Path(__file__).parent.parent.parent / "specs/009-option-optimizer/contracts/openapi_009.yaml"
    with open(contract_path) as f:
        return yaml.safe_load(f)


def validate_schema(data: dict, schema_ref: str, spec: dict) -> list[str]:
    """
    Validate data against OpenAPI schema reference.

    Returns list of validation errors, empty if valid.

    Args:
        data: Data to validate
        schema_ref: Schema reference like '#/components/schemas/OptimizeResponse'
        spec: OpenAPI specification dict
    """
    errors = []

    # Extract schema from reference
    if not schema_ref.startswith('#/components/schemas/'):
        errors.append(f"Invalid schema reference: {schema_ref}")
        return errors

    schema_name = schema_ref.split('/')[-1]
    schema = spec['components']['schemas'].get(schema_name)

    if not schema:
        errors.append(f"Schema not found: {schema_name}")
        return errors

    # Validate required fields
    if 'required' in schema:
        for field in schema['required']:
            if field not in data:
                errors.append(f"Missing required field: {field}")

    # Validate properties
    if 'properties' in schema:
        for key, value in data.items():
            if key not in schema['properties']:
                errors.append(f"Unexpected field: {key}")
                continue

            prop_schema = schema['properties'][key]
            prop_type = prop_schema.get('type')

            # Type validation
            if prop_type == 'string' and not isinstance(value, str):
                errors.append(f"Field {key} must be string, got {type(value).__name__}")
            elif prop_type == 'number' and not isinstance(value, (int, float)):
                errors.append(f"Field {key} must be number, got {type(value).__name__}")
            elif prop_type == 'integer' and not isinstance(value, int):
                errors.append(f"Field {key} must be integer, got {type(value).__name__}")
            elif prop_type == 'boolean' and not isinstance(value, bool):
                errors.append(f"Field {key} must be boolean, got {type(value).__name__}")
            elif prop_type == 'array' and not isinstance(value, list):
                errors.append(f"Field {key} must be array, got {type(value).__name__}")
            elif prop_type == 'object' and not isinstance(value, dict):
                errors.append(f"Field {key} must be object, got {type(value).__name__}")

            # Enum validation
            if 'enum' in prop_schema and value not in prop_schema['enum']:
                errors.append(f"Field {key} value '{value}' not in enum: {prop_schema['enum']}")

            # Minimum validation
            if 'minimum' in prop_schema and isinstance(value, (int, float)):
                if value < prop_schema['minimum']:
                    errors.append(f"Field {key} value {value} below minimum {prop_schema['minimum']}")

            # Nested array validation
            if prop_type == 'array' and isinstance(value, list) and 'items' in prop_schema:
                items_schema = prop_schema['items']
                if '$ref' in items_schema:
                    # Validate each array item recursively
                    for idx, item in enumerate(value):
                        item_errors = validate_schema(item, items_schema['$ref'], spec)
                        errors.extend([f"{key}[{idx}].{err}" for err in item_errors])

            # Nested object validation
            if '$ref' in prop_schema:
                nested_errors = validate_schema(value, prop_schema['$ref'], spec)
                errors.extend([f"{key}.{err}" for err in nested_errors])

    return errors


def test_optimize_response_schema_compliance():
    """Test OptimizeResponse matches openapi_009.yaml schema (FR-048-FR-055)."""
    spec = load_openapi_spec()

    # Example response structure per FR-048, FR-049, FR-054, FR-055
    response = {
        "top_10": [
            {
                "structure_type": "Iron Condor",
                "legs": [
                    {
                        "side": "short",
                        "option_type": "put",
                        "strike": 450.0,
                        "expiry": "2025-11-22",
                        "quantity": 1,
                        "fill_price": 2.15,
                        "bid": 2.10,
                        "ask": 2.20
                    },
                    {
                        "side": "long",
                        "option_type": "put",
                        "strike": 445.0,
                        "expiry": "2025-11-22",
                        "quantity": 1,
                        "fill_price": 1.35,
                        "bid": 1.30,
                        "ask": 1.40
                    },
                    {
                        "side": "short",
                        "option_type": "call",
                        "strike": 480.0,
                        "expiry": "2025-11-22",
                        "quantity": 1,
                        "fill_price": 2.25,
                        "bid": 2.20,
                        "ask": 2.30
                    },
                    {
                        "side": "long",
                        "option_type": "call",
                        "strike": 485.0,
                        "expiry": "2025-11-22",
                        "quantity": 1,
                        "fill_price": 1.40,
                        "bid": 1.35,
                        "ask": 1.45
                    }
                ],
                "metrics": {
                    "E_PnL": 625.0,
                    "CI_epnl": [520.0, 730.0],
                    "POP_0": 0.72,
                    "POP_target": 0.68,
                    "ROC": 0.045,
                    "MaxLoss_trade": -725.0,
                    "VaR_5": -650.0,
                    "CVaR_5": -700.0,
                    "Delta": -0.02,
                    "Theta": 25.0,
                    "Gamma": -0.05,
                    "Vega": -15.0,
                    "path_count": 5000
                },
                "score": 0.78,
                "score_decomposition": {
                    "pop_contrib": 0.25,
                    "roc_contrib": 0.18,
                    "theta_contrib": 0.08,
                    "tail_penalty": 0.12,
                    "delta_penalty": 0.01,
                    "gamma_penalty": 0.02,
                    "vega_penalty": 0.01
                },
                "order_json": {
                    "symbol": "NVDA",
                    "strategy": "IRON_CONDOR",
                    "instructions": "BUY_TO_OPEN"
                }
            }
        ],
        "top_100_cache_path": "/tmp/qse_top100_NVDA_20251121.json",
        "diagnostics": {
            "stage_counts": {
                "Stage 0 (expiries)": 4,
                "Stage 1 (strikes)": 45,
                "Stage 2 (structures)": 1024,
                "Stage 3 (survivors)": 187,
                "Stage 4 (MC scored)": 187
            },
            "rejection_breakdown": {
                "capital_filter": 342,
                "maxloss_filter": 128,
                "epnl_filter": 89,
                "pop_filter": 278
            },
            "pricer_warnings": [
                "Bjerksund convergence failed for NVDA 485C, fallback to BS"
            ],
            "adaptive_paths": {
                "initial": 5000,
                "doubled": True,
                "final": 10000,
                "reason": "CI width 0.28 exceeded threshold 0.20"
            },
            "hints": [
                "Consider widening max_capital to capture more candidates",
                "High rejection on POP filter - try lowering min_pop_breakeven"
            ]
        },
        "runtime_seconds": 28.5
    }

    # Validate against schema
    errors = validate_schema(response, '#/components/schemas/OptimizeResponse', spec)

    # Assert no validation errors
    assert not errors, f"Schema validation errors:\n" + "\n".join(errors)


def test_optimize_response_required_fields():
    """Test OptimizeResponse contains all required fields (FR-048)."""
    spec = load_openapi_spec()
    schema = spec['components']['schemas']['OptimizeResponse']

    # Minimal valid response
    response = {
        "top_10": [],
        "diagnostics": {
            "stage_counts": {},
            "rejection_breakdown": {},
            "hints": []
        }
    }

    errors = validate_schema(response, '#/components/schemas/OptimizeResponse', spec)
    assert not errors, f"Required fields validation failed:\n" + "\n".join(errors)


def test_optimize_response_empty_results_with_diagnostics():
    """Test empty top_10 list includes diagnostic hints (FR-054, FR-055)."""
    spec = load_openapi_spec()

    # Empty results scenario per FR-054
    response = {
        "top_10": [],
        "diagnostics": {
            "stage_counts": {
                "Stage 0 (expiries)": 4,
                "Stage 1 (strikes)": 52,
                "Stage 2 (structures)": 1200,
                "Stage 3 (survivors)": 0,
                "Stage 4 (MC scored)": 0
            },
            "rejection_breakdown": {
                "capital_filter": 0,
                "maxloss_filter": 1200,
                "epnl_filter": 0,
                "pop_filter": 0
            },
            "hints": [
                "All 1200 structures rejected by MaxLoss filter (MaxLoss/capital > 0.05)",
                "Suggestion: Increase max_loss_pct or widen structure widths",
                "Stage 3 hard filters eliminated all candidates - consider relaxing constraints"
            ]
        },
        "runtime_seconds": 12.3
    }

    errors = validate_schema(response, '#/components/schemas/OptimizeResponse', spec)
    assert not errors, f"Empty results validation failed:\n" + "\n".join(errors)

    # Verify diagnostic hints present
    assert len(response['diagnostics']['hints']) > 0, "Empty results must include diagnostic hints"
    assert "All 1200 structures rejected" in response['diagnostics']['hints'][0]


def test_trade_structure_validation():
    """Test Trade schema with all leg types (FR-048, FR-050)."""
    spec = load_openapi_spec()

    # Bull Put Spread example
    trade = {
        "structure_type": "Bull Put Spread",
        "legs": [
            {
                "side": "short",
                "option_type": "put",
                "strike": 460.0,
                "expiry": "2025-11-22",
                "quantity": 1,
                "fill_price": 3.20,
                "bid": 3.15,
                "ask": 3.25
            },
            {
                "side": "long",
                "option_type": "put",
                "strike": 455.0,
                "expiry": "2025-11-22",
                "quantity": 1,
                "fill_price": 2.10,
                "bid": 2.05,
                "ask": 2.15
            }
        ],
        "metrics": {
            "E_PnL": 450.0,
            "CI_epnl": [380.0, 520.0],
            "POP_0": 0.68,
            "ROC": 0.038,
            "MaxLoss_trade": -390.0,
            "Delta": 0.12,
            "Theta": 18.0,
            "Gamma": -0.03,
            "Vega": -8.0,
            "path_count": 5000
        },
        "score": 0.72
    }

    errors = validate_schema(trade, '#/components/schemas/Trade', spec)
    assert not errors, f"Trade validation failed:\n" + "\n".join(errors)


def test_leg_enum_validation():
    """Test Leg schema enforces enums for side and option_type (FR-050)."""
    spec = load_openapi_spec()

    # Valid leg
    valid_leg = {
        "side": "long",
        "option_type": "call",
        "strike": 475.0,
        "expiry": "2025-11-22",
        "quantity": 1,
        "fill_price": 5.50
    }

    errors = validate_schema(valid_leg, '#/components/schemas/Leg', spec)
    assert not errors, f"Valid leg failed validation:\n" + "\n".join(errors)

    # Invalid side
    invalid_side_leg = {
        "side": "neutral",  # Invalid
        "option_type": "call",
        "strike": 475.0,
        "expiry": "2025-11-22",
        "quantity": 1
    }

    errors = validate_schema(invalid_side_leg, '#/components/schemas/Leg', spec)
    assert errors, "Invalid side should fail validation"
    assert any("not in enum" in err for err in errors), f"Expected enum error, got: {errors}"


def test_metrics_schema_completeness():
    """Test Metrics schema includes all MC outputs (FR-027-FR-031, FR-033)."""
    spec = load_openapi_spec()

    # Complete metrics per FR-027 through FR-033
    metrics = {
        "E_PnL": 600.0,
        "CI_epnl": [510.0, 690.0],  # FR-033 95% CI
        "POP_0": 0.70,  # FR-028 breakeven
        "POP_target": 0.65,  # FR-028 profit target
        "ROC": 0.042,  # FR-029 return on capital
        "MaxLoss_trade": -680.0,  # FR-030 tail risk
        "VaR_5": -620.0,  # FR-030 VaR
        "CVaR_5": -650.0,  # FR-030 CVaR
        "Delta": -0.01,  # FR-031 Greeks
        "Theta": 22.0,
        "Gamma": -0.04,
        "Vega": -12.0,
        "path_count": 5000  # FR-032 adaptive paths
    }

    errors = validate_schema(metrics, '#/components/schemas/Metrics', spec)
    assert not errors, f"Metrics validation failed:\n" + "\n".join(errors)


def test_diagnostics_schema_all_components():
    """Test Diagnostics schema includes all FR-054, FR-055, FR-075 components."""
    spec = load_openapi_spec()

    # Complete diagnostics per FR-054, FR-055, FR-075
    diagnostics = {
        "stage_counts": {  # FR-054
            "Stage 0 (expiries)": 4,
            "Stage 1 (strikes)": 48,
            "Stage 2 (structures)": 980,
            "Stage 3 (survivors)": 165,
            "Stage 4 (MC scored)": 165
        },
        "rejection_breakdown": {  # FR-054
            "capital_filter": 315,
            "maxloss_filter": 142,
            "epnl_filter": 98,
            "pop_filter": 260
        },
        "pricer_warnings": [  # FR-021, FR-022
            "Bjerksund convergence failed for XYZ 500C, fallback to BS",
            "Missing IV data for ABC 520P, using ATM IV proxy"
        ],
        "adaptive_paths": {  # FR-032, FR-033
            "initial": 5000,
            "doubled": True,
            "final": 10000,
            "reason": "CI width 0.26 > threshold 0.20"
        },
        "hints": [  # FR-055
            "High rejection on capital filter - consider increasing max_capital",
            "Strong-bullish regime but low POP - check IV assumptions"
        ]
    }

    errors = validate_schema(diagnostics, '#/components/schemas/Diagnostics', spec)
    assert not errors, f"Diagnostics validation failed:\n" + "\n".join(errors)
