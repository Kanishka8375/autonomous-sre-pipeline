import json
import re
import logging
from typing import List, Optional
from pathlib import Path
import datetime

from sre_pipeline.models import LogEntry, LogLevel

class LogIngester:
    """Ingests log files from a directory and parses them into LogEntry objects."""
    
    def __init__(self, directory: str) -> None:
        """Initialize the LogIngester with a target directory."""
        self.directory: Path = Path(directory)
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.pt_pattern: re.Pattern[str] = re.compile(
            r'(?P<timestamp>\S+ \S+)\s+(?P<level>\w+)\s+(?P<service>\S+)\s+(?P<message>.+)'
        )

    def ingest(self) -> List[LogEntry]:
        """Ingest all log files in the directory."""
        entries: List[LogEntry] = []
        if not self.directory.exists() or not self.directory.is_dir():
            return entries

        for file_path in self.directory.iterdir():
            if file_path.is_file():
                entries.extend(self._parse_file(file_path))
        return entries

    def _parse_file(self, file_path: Path) -> List[LogEntry]:
        """Parse a single file line by line."""
        entries: List[LogEntry] = []
        try:
            with file_path.open('r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = self._parse_line(line)
                    if entry:
                        entries.append(entry)
                    else:
                        self.logger.warning("Skipping malformed line: %s", line)
        except OSError as e:
            self.logger.warning("Error reading file %s: %s", file_path, e)
        return entries

    def _parse_line(self, line: str) -> Optional[LogEntry]:
        """Attempt to parse a line as JSON, then fallback to plaintext."""
        if line.startswith('{') and line.endswith('}'):
            try:
                data = json.loads(line)
                timestamp_str = data['timestamp'].replace('Z', '+00:00')
                return LogEntry(
                    timestamp=datetime.datetime.fromisoformat(timestamp_str),
                    level=LogLevel(data['level']),
                    service=data['service'],
                    message=data['message'],
                    raw=line,
                    source_format="json"
                )
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

        match = self.pt_pattern.match(line)
        if match:
            try:
                return LogEntry(
                    timestamp=datetime.datetime.fromisoformat(match.group('timestamp')),
                    level=LogLevel(match.group('level')),
                    service=match.group('service'),
                    message=match.group('message'),
                    raw=line,
                    source_format="plaintext"
                )
            except ValueError:
                pass
        return None
