"""Contract tests for monitor command against openapi_009.yaml (T045, FR-063-FR-070)."""

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
            elif prop_type == 'array' and not isinstance(value, list):
                errors.append(f"Field {key} must be array, got {type(value).__name__}")
            elif prop_type == 'object' and not isinstance(value, dict):
                errors.append(f"Field {key} must be object, got {type(value).__name__}")

            # Nested object validation
            if '$ref' in prop_schema:
                nested_errors = validate_schema(value, prop_schema['$ref'], spec)
                errors.extend([f"{key}.{err}" for err in nested_errors])

            # Array item validation
            if prop_type == 'array' and isinstance(value, list) and 'items' in prop_schema:
                items_schema = prop_schema['items']
                if items_schema.get('type') == 'string':
                    for idx, item in enumerate(value):
                        if not isinstance(item, str):
                            errors.append(f"{key}[{idx}] must be string")

    return errors


def test_monitor_request_schema_compliance():
    """Test MonitorRequest matches openapi_009.yaml schema (FR-063, FR-064)."""
    spec = load_openapi_spec()

    # Example request per FR-063, FR-064
    request = {
        "position_file": "/tmp/qse_position_NVDA_20251121.json",
        "interval_seconds": 300,
        "alert_config": {
            "loss_threshold_pct": 0.50,
            "profit_target_pct": 0.80,
            "time_decay_warning_hours": 2
        }
    }

    errors = validate_schema(request, '#/components/schemas/MonitorRequest', spec)
    assert not errors, f"Schema validation errors:\n" + "\n".join(errors)


def test_monitor_response_schema_compliance():
    """Test MonitorResponse matches openapi_009.yaml schema (FR-066-FR-070)."""
    spec = load_openapi_spec()

    # Example response per FR-066, FR-067, FR-068
    response = {
        "status": "running",
        "last_metrics": {
            "E_PnL": 420.0,  # Position now up $420 from entry
            "CI_epnl": [360.0, 480.0],
            "POP_0": 0.75,  # Improved probability
            "ROC": 0.035,
            "MaxLoss_trade": -580.0,  # Reduced max loss
            "VaR_5": -520.0,
            "CVaR_5": -550.0,
            "Delta": -0.01,
            "Theta": 18.0,  # Decaying
            "Gamma": -0.03,
            "Vega": -10.0,
            "path_count": 5000
        },
        "alerts_triggered": [
            "PROFIT: Position up 70% of max profit target ($420/$600)",
            "TIME_DECAY: 1.5 hours remaining, theta decay $18/hour"
        ],
        "next_run_eta_seconds": 300
    }

    errors = validate_schema(response, '#/components/schemas/MonitorResponse', spec)
    assert not errors, f"Schema validation errors:\n" + "\n".join(errors)


def test_monitor_response_with_loss_alert():
    """Test MonitorResponse includes loss threshold alerts (FR-067)."""
    spec = load_openapi_spec()

    # Loss scenario per FR-067
    response = {
        "status": "running",
        "last_metrics": {
            "E_PnL": -350.0,  # Position down $350
            "CI_epnl": [-420.0, -280.0],
            "POP_0": 0.42,  # Probability dropped
            "ROC": -0.029,
            "MaxLoss_trade": -720.0,
            "Delta": 0.08,
            "Theta": 12.0,
            "Gamma": -0.06,
            "Vega": -18.0,
            "path_count": 5000
        },
        "alerts_triggered": [
            "LOSS: Position down $350, exceeds 50% loss threshold (-$300)",
            "POP_DECLINE: Probability of profit dropped from 68% to 42%",
            "SUGGESTION: Consider closing position to limit further losses"
        ],
        "next_run_eta_seconds": 300
    }

    errors = validate_schema(response, '#/components/schemas/MonitorResponse', spec)
    assert not errors, f"Loss alert validation failed:\n" + "\n".join(errors)

    # Verify loss alert present
    assert any("LOSS:" in alert for alert in response['alerts_triggered'])


def test_monitor_response_no_alerts():
    """Test MonitorResponse with empty alerts array (FR-066, FR-068)."""
    spec = load_openapi_spec()

    # Normal monitoring with no alerts
    response = {
        "status": "running",
        "last_metrics": {
            "E_PnL": 150.0,
            "POP_0": 0.68,
            "ROC": 0.012,
            "MaxLoss_trade": -650.0,
            "Delta": -0.02,
            "Theta": 20.0,
            "Gamma": -0.04,
            "Vega": -12.0,
            "path_count": 5000
        },
        "alerts_triggered": [],
        "next_run_eta_seconds": 300
    }

    errors = validate_schema(response, '#/components/schemas/MonitorResponse', spec)
    assert not errors, f"No alerts validation failed:\n" + "\n".join(errors)


def test_monitor_response_status_values():
    """Test MonitorResponse status field accepts valid values (FR-069)."""
    spec = load_openapi_spec()

    valid_statuses = ["running", "stopped", "completed", "error"]

    for status in valid_statuses:
        response = {
            "status": status,
            "last_metrics": {
                "E_PnL": 100.0,
                "POP_0": 0.65,
                "Delta": 0.0,
                "Theta": 15.0,
                "path_count": 5000
            },
            "alerts_triggered": [],
            "next_run_eta_seconds": 300
        }

        errors = validate_schema(response, '#/components/schemas/MonitorResponse', spec)
        assert not errors, f"Status '{status}' validation failed:\n" + "\n".join(errors)


def test_monitor_response_with_exit_recommendation():
    """Test MonitorResponse includes exit recommendations (FR-070)."""
    spec = load_openapi_spec()

    # Profit target hit scenario per FR-070
    response = {
        "status": "running",
        "last_metrics": {
            "E_PnL": 580.0,  # Close to max profit
            "CI_epnl": [520.0, 640.0],
            "POP_0": 0.82,
            "ROC": 0.048,
            "MaxLoss_trade": -420.0,
            "Delta": -0.01,
            "Theta": 8.0,  # Low remaining theta
            "Gamma": -0.02,
            "Vega": -5.0,
            "path_count": 5000
        },
        "alerts_triggered": [
            "PROFIT_TARGET: Position reached 97% of max profit ($580/$600)",
            "EXIT_RECOMMENDATION: Close position now - limited upside remaining",
            "THETA_DECAY: Theta decay reduced to $8/hour, diminishing returns"
        ],
        "next_run_eta_seconds": 0  # Stop monitoring
    }

    errors = validate_schema(response, '#/components/schemas/MonitorResponse', spec)
    assert not errors, f"Exit recommendation validation failed:\n" + "\n".join(errors)

    # Verify exit recommendation present
    assert any("EXIT_RECOMMENDATION:" in alert for alert in response['alerts_triggered'])


def test_monitor_request_minimal_required_fields():
    """Test MonitorRequest with only required fields (FR-063)."""
    spec = load_openapi_spec()
    schema = spec['components']['schemas']['MonitorRequest']

    # Minimal request with only required fields
    request = {
        "position_file": "/tmp/qse_position.json"
    }

    errors = validate_schema(request, '#/components/schemas/MonitorRequest', spec)
    assert not errors, f"Minimal request validation failed:\n" + "\n".join(errors)


def test_monitor_response_metrics_reuse_optimize_schema():
    """Test MonitorResponse last_metrics uses same Metrics schema as OptimizeResponse (FR-066, FR-071)."""
    spec = load_openapi_spec()

    # Monitor response with metrics
    response = {
        "status": "running",
        "last_metrics": {
            "E_PnL": 500.0,
            "CI_epnl": [430.0, 570.0],
            "POP_0": 0.71,
            "POP_target": 0.67,
            "ROC": 0.041,
            "MaxLoss_trade": -620.0,
            "VaR_5": -580.0,
            "CVaR_5": -600.0,
            "Delta": -0.02,
            "Theta": 19.0,
            "Gamma": -0.04,
            "Vega": -11.0,
            "path_count": 5000
        },
        "alerts_triggered": [],
        "next_run_eta_seconds": 300
    }

    # Validate full response
    errors = validate_schema(response, '#/components/schemas/MonitorResponse', spec)
    assert not errors, f"Monitor response validation failed:\n" + "\n".join(errors)

    # Validate metrics specifically
    metrics_errors = validate_schema(response['last_metrics'], '#/components/schemas/Metrics', spec)
    assert not metrics_errors, f"Metrics reuse validation failed:\n" + "\n".join(metrics_errors)


def test_monitor_multiple_alert_types():
    """Test MonitorResponse can include multiple simultaneous alerts (FR-067, FR-068)."""
    spec = load_openapi_spec()

    # Complex scenario with multiple alerts
    response = {
        "status": "running",
        "last_metrics": {
            "E_PnL": 280.0,
            "CI_epnl": [210.0, 350.0],
            "POP_0": 0.58,
            "ROC": 0.023,
            "MaxLoss_trade": -720.0,
            "Delta": 0.15,  # High directional exposure
            "Theta": 6.0,  # Low decay
            "Gamma": -0.08,  # High gamma risk
            "Vega": -25.0,  # High vega exposure
            "path_count": 10000  # Doubled for CI tightening
        },
        "alerts_triggered": [
            "PROFIT: Position up $280 (47% of target)",
            "DELTA_EXPOSURE: Delta 0.15 indicates directional risk",
            "GAMMA_RISK: High gamma -0.08 may cause rapid P&L swings",
            "VEGA_EXPOSURE: High vega -25.0 vulnerable to IV changes",
            "TIME_DECAY: Low theta $6/hour, limited income remaining"
        ],
        "next_run_eta_seconds": 300
    }

    errors = validate_schema(response, '#/components/schemas/MonitorResponse', spec)
    assert not errors, f"Multiple alerts validation failed:\n" + "\n".join(errors)

    # Verify multiple alert types present
    assert len(response['alerts_triggered']) >= 3, "Should have multiple simultaneous alerts"
