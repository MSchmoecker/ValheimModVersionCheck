import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('NEXUS_API_KEY')


def mod_route(mod_id):
    return f"https://api.nexusmods.com/v1/games/valheim/mods/{mod_id}.json"


def updated_route():
    return f"https://api.nexusmods.com/v1/games/valheim/mods/updated.json?period=1m"


def _fetch_mod(mods, mod_id, force=False):
    if not force and str(mod_id) in mods:
        return

    print("Fetching mod from Nexus", mod_id)

    route = mod_route(mod_id)
    r = requests.get(route, headers={'apikey': API_KEY})

    if r.status_code == 200:
        mods[str(mod_id)] = r.json()
    else:
        mods[str(mod_id)] = None

    with open('nexus_mods.json', 'w') as f:
        json.dump(mods, f, indent=4)


def updated_mods_highest_id():
    r = requests.get(updated_route(), headers={'apikey': API_KEY})
    if r.status_code == 200:
        return max(r.json(), key=lambda x: x['mod_id'])['mod_id']

    raise Exception("Failed to fetch updated mods with status code", r.status_code)


def fetch_online():
    mods = {}

    if os.path.isfile('nexus_mods.json'):
        with open('nexus_mods.json', 'r+') as f:
            mods = json.load(f)

    highest_id = updated_mods_highest_id()

    for mod_id in range(0, highest_id):
        _fetch_mod(mods, mod_id)

    return mods
