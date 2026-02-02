import yaml
import os
from typing import Dict, Any

class ConfigLoader:
    """Singleton-style loader for YAML configurations."""
    
    @staticmethod
    def load(path: str = "configs/default_config.yaml") -> Dict[str, Any]:
        if not os.path.exists(path):
            path = os.path.join(os.getcwd(), path)
            if not os.path.exists(path):
                raise FileNotFoundError(f"Config file not found at: {path}")

        with open(path, 'r') as f:
            try:
                config = yaml.safe_load(f)
                return config
            except yaml.YAMLError as exc:
                raise ValueError(f"Error parsing YAML: {exc}")