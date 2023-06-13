import json
import os
import requests
import logging
from pathlib import Path

import app_version
from src import env


def mod_route(mod_id):
    return f"https://api.nexusmods.com/v1/games/valheim/mods/{mod_id}.json"


def updated_route():
    return f"https://api.nexusmods.com/v1/games/valheim/mods/updated.json?period=1m"


default_headers = {
    'apikey': env.NEXUS_API_KEY,
    "Application-Name": "Valheim Mod Version Check",
    "Application-Version": str(app_version.app_version)
}

file_path = Path("data/nexus_mods.json")


def _fetch_mod(mods, mod_id, force=False):
    if not force and str(mod_id) in mods:
        return

    if str(mod_id) not in mods:
        logging.info(f"Found new mod from Nexus with id {mod_id}")
    else:
        logging.info(f"Updating mod from Nexus with id {mod_id}")

    r = requests.get(mod_route(mod_id), headers={**default_headers})

    if r.status_code == 200:
        mods[str(mod_id)] = r.json()
    else:
        mods[str(mod_id)] = None

    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(mods, f, indent=4)


def get_highest_id_of_updated_mods():
    try:
        r = requests.get(updated_route(), headers={**default_headers})
    except Exception as e:
        logging.exception(f"Failed to fetch updated nexus mods: {e}")
        return None

    if r.status_code == 200:
        return max(r.json(), key=lambda x: x['mod_id'])['mod_id']

    logging.error(f"Failed to fetch updated mods with status code {r.status_code}")
    return None


def add_new_mods(mods):
    highest_id = get_highest_id_of_updated_mods()

    if highest_id:
        for mod_id in range(0, highest_id):
            _fetch_mod(mods, mod_id + 1)


def update_mods(mods):
    try:
        r = requests.get(updated_route(), headers={**default_headers})
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
            _fetch_mod(mods, mod_id, force=True)


def fetch_online():
    if not env.NEXUS_API_KEY:
        return {}

    mods = {}

    if os.path.isfile(file_path):
        with open(file_path, 'r+') as f:
            mods = json.load(f)

    add_new_mods(mods)
    update_mods(mods)

    return mods
