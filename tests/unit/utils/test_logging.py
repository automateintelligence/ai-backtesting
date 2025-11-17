import json
import logging

import pytest

from quant_scenario_engine.utils.logging import JSONFormatter, configure_logging, get_logger


def test_json_formatter_includes_fields():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.run_id = "abc"
    record.component = "loader"
    formatted = JSONFormatter().format(record)
    payload = json.loads(formatted)
    assert payload["message"] == "hello"
    assert payload["run_id"] == "abc"
    assert payload["component"] == "loader"


def test_configure_logging_and_get_logger(capsys):
    configure_logging(run_id="rid", component="comp", level=logging.INFO)
    logger = get_logger("unit", run_id="rid2", component="comp2")
    logger.info("hi", extra={"duration_ms": 10})
    captured = capsys.readouterr().out
    payload = json.loads(captured.strip())
    assert payload["run_id"] == "rid2"
    assert payload["component"] == "comp2"
    assert payload["duration_ms"] == 10
