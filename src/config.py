import yaml
import os
from typing import List, Optional
from pydantic import BaseModel

config_file_path = os.path.join("config", "config.yml")


class GameConfig(BaseModel):
    name: str
    bepinex: List[str]
    thunderstore: Optional[str] = None
    nexus: Optional[str] = None


def get_games() -> List[GameConfig]:
    with open(config_file_path, "r") as f:
        config = yaml.safe_load(f)

    return [GameConfig(**game) for game in config["games"]]
