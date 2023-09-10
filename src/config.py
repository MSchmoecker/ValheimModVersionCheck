import yaml
import os

config_file_path = os.path.join("config", "config.yml")


def get_thunderstore_list():
    with open(config_file_path, "r") as f:
        config = yaml.safe_load(f)

    return [game["thunderstore"] for game in config["games"] if "thunderstore" in game]
