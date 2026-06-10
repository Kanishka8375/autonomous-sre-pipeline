import json
import logging
import datetime
from typing import Any, Optional

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.datetime.fromtimestamp(record.created, datetime.timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        
        # Add any extra arguments passed via extra=...
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", "filename", 
                          "funcName", "id", "levelname", "levelno", "lineno", "module", 
                          "msecs", "message", "msg", "name", "pathname", "process", 
                          "processName", "relativeCreated", "stack_info", "thread", "threadName"]:
                log_data[key] = value
                
        return json.dumps(log_data)

def setup_structured_logging(level: int = logging.INFO, handler: Optional[logging.Handler] = None) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)
        
    if handler is None:
        handler = logging.StreamHandler()
        
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)
