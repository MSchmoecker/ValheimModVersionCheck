import yaml
import os
from typing import List, Optional
from pydantic import BaseModel

config_file_path = os.path.join("config", "config.yml")


class BepInExConfig(BaseModel):
    log_names: List[str]


class ThunderstoreConfig(BaseModel):
    community: str


class NexusConfig(BaseModel):
    game_domain: str


class GameConfig(BaseModel):
    name: str
    bepinex: BepInExConfig
    thunderstore: ThunderstoreConfig
    nexus: Optional[NexusConfig] = None


def get_games() -> List[GameConfig]:
    with open(config_file_path, "r") as f:
        config = yaml.safe_load(f)

    return [GameConfig(**game) for game in config["games"]]
