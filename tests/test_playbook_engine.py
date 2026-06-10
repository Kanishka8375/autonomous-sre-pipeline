import pytest
import os
import yaml
from pathlib import Path
from sre_pipeline.playbook_engine import PlaybookEngine
from sre_pipeline.models import Playbook

def test_playbook_engine_loads_yaml(tmp_path: Path) -> None:
    playbooks_dir = tmp_path / "playbooks"
    playbooks_dir.mkdir()
    
    playbook_data = {
        "rule_id": "CRITICAL_LOG",
        "version": "1.0.0",
        "requires_human_approval": False,
        "steps": [
            {"order": 1, "action": "restart_service", "timeout_seconds": 60}
        ]
    }
    
    with open(playbooks_dir / "restart.yaml", "w") as f:
        yaml.dump(playbook_data, f)
        
    engine = PlaybookEngine(playbooks_dir=str(playbooks_dir))
    playbook = engine.get_playbook("CRITICAL_LOG")
    
    assert playbook is not None
    assert playbook.rule_id == "CRITICAL_LOG"
    assert playbook.version == "1.0.0"
    assert len(playbook.steps) == 1
    assert playbook.steps[0].action.value == "restart_service"

def test_playbook_engine_not_found(tmp_path: Path) -> None:
    engine = PlaybookEngine(playbooks_dir=str(tmp_path))
    assert engine.get_playbook("non_existent") is None
