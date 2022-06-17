import datetime
import logging
from typing import Dict
from packaging import version
from src import Mod, clean_name


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


def compare_mods(mods_local, mods_online: Dict[str, Mod]):
    time_threshold = datetime.datetime.now() - datetime.timedelta(days=30 * 6)
    result = ""

    for mod in mods_local:
        raw_name = mods_local[mod]["raw_name"]
        mod_version = mods_local[mod]["version"]

        if mod not in mods_online.keys():
            logging.info(f"{raw_name} not found!")
            continue

        outdated = version.parse(mod_version) < version.parse(mods_online[mod].version)
        old = mods_online[mod].updated < time_threshold

        if outdated or old:
            result += f"{raw_name}\n"

        if outdated:
            result += f"\tis outdated {mod_version} -> {mods_online[mod].version}\n"

        if old:
            result += f"\tis old {mods_online[mod].updated}\n"

        if version.parse(mod_version) > version.parse(mods_online[mod].version):
            continue
            result += f"{raw_name} is newer"
            result += f"\t{mod_version} -> {mods_online[mod].version}\n"

    return result
