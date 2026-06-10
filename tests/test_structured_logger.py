import pytest
import json
import logging
from io import StringIO
from sre_pipeline.structured_logger import setup_structured_logging

def test_structured_logger() -> None:
    # Capture log output
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    
    # Configure the logger using our setup method
    setup_structured_logging(level=logging.INFO, handler=handler)
    
    logger = logging.getLogger("test_structured_logger")
    logger.info("Structured log message", extra={"service": "auth", "rule_id": "CRITICAL_LOG"})
    
    log_output = stream.getvalue()
    assert log_output.strip() != ""
    
    parsed = json.loads(log_output.splitlines()[-1])
    
    # Should include JSON fields
    assert parsed["message"] == "Structured log message"
    assert parsed["service"] == "auth"
    assert parsed["rule_id"] == "CRITICAL_LOG"
    assert "timestamp" in parsed
    assert "level" in parsed
    assert parsed["level"] == "INFO"

    # Reset logging
    logging.getLogger().removeHandler(handler)
