import json
import os
import requests
import logging
from pathlib import Path

import app_version
from src import env


def file_path(game_domain: str):
    return Path(os.path.join("data", f"{game_domain}_nexus_mods.json"))


def mod_route(game_domain: str, mod_id):
    return f"https://api.nexusmods.com/v1/games/{game_domain}/mods/{mod_id}.json"


def updated_route(game_domain: str):
    return f"https://api.nexusmods.com/v1/games/{game_domain}/mods/updated.json?period=1m"


default_headers = {
    'apikey': env.NEXUS_API_KEY,
    "Application-Name": "Mod Version Check",
    "Application-Version": str(app_version.app_version)
}


def _fetch_mod(game_domain: str, mods, mod_id, force=False):
    if not force and str(mod_id) in mods:
        return

    if str(mod_id) not in mods:
        logging.info(f"Found new mod from Nexus with id {mod_id}")
    else:
        logging.info(f"Updating mod from Nexus with id {mod_id}")

    r = requests.get(mod_route(game_domain, mod_id), headers={**default_headers})

    if r.status_code == 200:
        mods[str(mod_id)] = r.json()
    else:
        mods[str(mod_id)] = None

    file_path(game_domain).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path(game_domain), 'w') as f:
        json.dump(mods, f, indent=4)


def get_highest_id_of_updated_mods(game_domain: str):
    try:
        r = requests.get(updated_route(game_domain), headers={**default_headers})
    except Exception as e:
        logging.exception(f"Failed to fetch updated nexus mods: {e}")
        return None

    if r.status_code == 200:
        return max(r.json(), key=lambda x: x['mod_id'])['mod_id']

    logging.error(f"Failed to fetch updated mods with status code {r.status_code}")
    return None


def add_new_mods(game_domain: str, mods):
    highest_id = get_highest_id_of_updated_mods(game_domain)

    if highest_id:
        for mod_id in range(0, highest_id):
            _fetch_mod(game_domain, mods, mod_id + 1)


def update_mods(game_domain: str, mods):
    try:
        r = requests.get(updated_route(game_domain), headers={**default_headers})
    except Exception as e:
        logging.exception(f"Failed to fetch updated nexus mods: {e}")
        return

    if r.status_code == 200:
        updated = r.json()
    else:
        logging.error(f"Failed to fetch updated mods with status code {r.status_code}")
        return

    for mod in updated:
        mod_id = str(mod['mod_id'])

        if mod['latest_file_update'] > mods[mod_id]['updated_timestamp']:
            _fetch_mod(game_domain, mods, mod_id, force=True)


def fetch_online(game_domain: str) -> dict:
    if not env.NEXUS_API_KEY:
        return {}

    mods = {}

    if os.path.isfile(file_path(game_domain)):
        with open(file_path(game_domain), 'r+') as f:
            mods = json.load(f)

    add_new_mods(game_domain, mods)
    update_mods(game_domain, mods)

    return mods
