import json
import re
import logging
from typing import List, Optional, cast
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
        self.positions_file: Path = self.directory / ".positions.json"

    def _load_positions(self) -> dict[str, int]:
        if self.positions_file.exists():
            try:
                with self.positions_file.open('r') as f:
                    return cast(dict[str, int], json.load(f))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_positions(self, positions: dict[str, int]) -> None:
        try:
            with self.positions_file.open('w') as f:
                json.dump(positions, f)
        except OSError as e:
            self.logger.warning("Failed to save positions: %s", e)

    def ingest(self) -> List[LogEntry]:
        """Ingest all log files in the directory."""
        entries: List[LogEntry] = []
        if not self.directory.exists() or not self.directory.is_dir():
            return entries

        positions = self._load_positions()

        for file_path in self.directory.iterdir():
            if file_path.is_file() and file_path.name != ".positions.json":
                new_entries, new_pos = self._parse_file(file_path, positions.get(file_path.name, 0))
                entries.extend(new_entries)
                positions[file_path.name] = new_pos
        
        self._save_positions(positions)
        return entries

    def _parse_file(self, file_path: Path, start_pos: int) -> tuple[List[LogEntry], int]:
        """Parse a single file line by line."""
        entries: List[LogEntry] = []
        current_pos = start_pos
        try:
            file_size = file_path.stat().st_size
            if file_size < start_pos:
                # File was truncated/rotated
                start_pos = 0
                current_pos = 0

            with file_path.open('r', encoding='utf-8') as f:
                f.seek(start_pos)
                for line in f:
                    # Update position
                    current_pos += len(line.encode('utf-8'))
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
        return entries, current_pos

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
