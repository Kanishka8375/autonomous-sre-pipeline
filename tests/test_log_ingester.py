import pytest
from pathlib import Path
from sre_pipeline.log_ingester import LogIngester

@pytest.fixture
def log_dir(tmp_path: Path) -> Path:
    d = tmp_path / "logs"
    d.mkdir()
    return d

def test_file_position_tracking(log_dir: Path) -> None:
    log_file = log_dir / "app.log"
    log_file.write_text('{"timestamp": "2023-01-01T12:00:00Z", "level": "INFO", "service": "api", "message": "msg1"}\n')
    
    ingester = LogIngester(str(log_dir))
    entries = ingester.ingest()
    assert len(entries) == 1
    assert entries[0].message == "msg1"
    
    # Read again -> should be 0 entries because position is tracked
    entries2 = ingester.ingest()
    assert len(entries2) == 0
    
    # Append another line
    with log_file.open("a") as f:
        f.write('{"timestamp": "2023-01-01T12:01:00Z", "level": "ERROR", "service": "api", "message": "msg2"}\n')
    
    # Read again -> should only read the new line
    entries3 = ingester.ingest()
    assert len(entries3) == 1
    assert entries3[0].message == "msg2"

def test_file_truncation(log_dir: Path) -> None:
    log_file = log_dir / "app.log"
    log_file.write_text('{"timestamp": "2023-01-01T12:00:00Z", "level": "INFO", "service": "api", "message": "msg1"}\n')
    
    ingester = LogIngester(str(log_dir))
    assert len(ingester.ingest()) == 1
    
    # File is truncated and written with new content (simulate log rotation).
    # New string must be shorter than previous string to trigger simple file_size < start_pos check.
    log_file.write_text('{"timestamp": "2023-01-01T12:02:00Z", "level": "INFO", "service": "api", "message": "m"}\n')
    
    entries = ingester.ingest()
    assert len(entries) == 1
    assert entries[0].message == "m"

def test_multiple_files_tracking(log_dir: Path) -> None:
    file1 = log_dir / "app1.log"
    file2 = log_dir / "app2.log"
    
    file1.write_text('{"timestamp": "2023-01-01T12:00:00Z", "level": "INFO", "service": "api", "message": "msg1"}\n')
    file2.write_text('{"timestamp": "2023-01-01T12:00:00Z", "level": "INFO", "service": "api", "message": "msg2"}\n')
    
    ingester = LogIngester(str(log_dir))
    entries = ingester.ingest()
    assert len(entries) == 2
    
    entries = ingester.ingest()
    assert len(entries) == 0
