import os
import yaml
import logging
from typing import Dict, Optional, Any
from pathlib import Path
from sre_pipeline.models import Playbook, PlaybookStep, ActionType

logger = logging.getLogger(__name__)

class PlaybookEngine:
    def __init__(self, playbooks_dir: str = "playbooks") -> None:
        self.playbooks_dir = playbooks_dir
        self.playbooks: Dict[str, Playbook] = {}
        self._load_playbooks()

    def _load_playbooks(self) -> None:
        if not os.path.exists(self.playbooks_dir):
            logger.warning("Playbooks directory not found: %s", self.playbooks_dir)
            return

        for entry in os.listdir(self.playbooks_dir):
            if entry.endswith((".yml", ".yaml")):
                filepath = os.path.join(self.playbooks_dir, entry)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if isinstance(data, dict):
                            # Validate required fields
                            required_fields = ["rule_id", "version", "steps", "requires_human_approval"]
                            if all(k in data for k in required_fields):
                                steps = []
                                for step_data in data["steps"]:
                                    # Convert action string to enum
                                    action_enum = None
                                    for a in ActionType:
                                        if a.value == step_data.get("action"):
                                            action_enum = a
                                            break
                                    if action_enum is None:
                                        action_enum = ActionType.NO_ACTION
                                        
                                    steps.append(PlaybookStep(
                                        order=step_data.get("order", 0),
                                        action=action_enum,
                                        condition=step_data.get("condition"),
                                        timeout_seconds=step_data.get("timeout_seconds", 30)
                                    ))
                                
                                playbook = Playbook(
                                    rule_id=data["rule_id"],
                                    version=str(data["version"]),
                                    steps=steps,
                                    requires_human_approval=data["requires_human_approval"],
                                    max_auto_executions_per_hour=data.get("max_auto_executions_per_hour", 3)
                                )
                                self.playbooks[playbook.rule_id] = playbook
                                logger.info("Loaded playbook: %s (v%s)", playbook.rule_id, playbook.version)
                            else:
                                logger.warning("Playbook %s is missing required fields", entry)
                except Exception as e:
                    logger.error("Failed to load playbook %s: %s", entry, e)

    def get_playbook(self, playbook_id: str) -> Optional[Playbook]:
        return self.playbooks.get(playbook_id)
