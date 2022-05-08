import datetime
import requests

from packaging import version

from modnames import clean_name

last_online_fetched: datetime = None
mods_online: dict = {}


def parse_created_date(target):
    return datetime.datetime.strptime(target["date_created"], "%Y-%m-%dT%H:%M:%S.%fZ")


def fetch_online():
    mods = {}
    r = requests.get("https://valheim.thunderstore.io/api/v1/package/")
    for mod in r.json():
        mod_name = clean_name(mod["name"]).lower()
        mod_version = mod["versions"][0]["version_number"]
        if mod_name not in mods:
            mods[mod_name] = {
                "version": mod_version,
                "updated": parse_created_date(mod["versions"][0])
            }
        else:
            if version.parse(mod_version) > version.parse(mods[mod_name]["version"]):
                mods[mod_name] = {
                    "version": mod_version,
                    "updated": parse_created_date(mod["versions"][0])
                }
    return mods


def parse_local(local_text, is_logfile: bool):
    mods = {}
    lines = local_text.splitlines()
    for i, line in enumerate(lines):
        if is_logfile:
            if not line.startswith("[Info   :   BepInEx] Loading ["):
                continue
            line = line[line.index("[", 1) + 1:line.index("]", 20)]

        mod_name = clean_name("".join(line.split(" ")[:-1])).lower()
        mods[mod_name] = {
            "raw_name": clean_name("".join(line.split(" ")[:-1])),
            "version": "".join(line.split(" ")[-1])
        }
    return mods


def compare_mods(mods_local):
    global last_online_fetched, mods_online

    if last_online_fetched is None or last_online_fetched < datetime.datetime.now() - datetime.timedelta(minutes=1):
        print("Fetch online ... ", end="")
        mods_online = fetch_online()
        print("done")
        last_online_fetched = datetime.datetime.now()

    time_threshold = datetime.datetime.now() - datetime.timedelta(days=30 * 6)
    result = ""

    for mod in mods_local:
        raw_name = mods_local[mod]["raw_name"]
        mod_version = mods_local[mod]["version"]

        if mod not in mods_online.keys():
            print(f"{raw_name} not found at Thunderstore")
            continue

        outdated = version.parse(mod_version) < version.parse(mods_online[mod]["version"])
        old = mods_online[mod]["updated"] < time_threshold

        if outdated or old:
            result += f"{raw_name}\n"

        if outdated:
            result += f"\tis outdated {mod_version} -> {mods_online[mod]['version']}\n"

        if old:
            result += f"\tis old {mods_online[mod]['updated']}\n"

        if version.parse(mod_version) > version.parse(mods_online[mod]["version"]):
            continue
            result += f"{raw_name} is newer"
            result += f"\t{mod_version} -> {mods_online[mod]['version']}\n"

    return result
