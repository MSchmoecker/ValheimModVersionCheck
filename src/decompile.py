import json
import logging
import os
import shutil
import tempfile

import requests
from readerwriterlock.rwlock import RWLockRead

from src import thunderstore

decompiled_mods_file_path = os.path.join("data", "decompiled_mods.json")


def fetch_mods(file_lock: RWLockRead):
    logging.info("Fetching Thunderstore ...")
    thunder_mods = thunderstore.fetch_online()
    write_lock = file_lock.gen_rlock()
    read_lock = file_lock.gen_rlock()
    decompiled_mods = read_extracted_mod_from_file(read_lock)

    mod_lookup = set()
    for mod in thunder_mods:
        mod_lookup.add(mod["full_name"])

    for mod in list(decompiled_mods.keys()):
        if mod not in mod_lookup:
            logging.info(f"Removing {mod} from decompiled mods, not longer on Thunderstore")
            del decompiled_mods[mod]

    for mod in thunder_mods:
        online_mod_name = mod["full_name"]
        online_name = mod["name"]
        online_mod_version = mod["versions"][0]["version_number"]
        download_url = mod["versions"][0]["download_url"]
        date_created = mod["versions"][0]["date_created"]
        is_deprecated = mod["is_deprecated"]

        if online_name != "BepInExPack_Valheim" and online_name != "r2modman":
            if online_mod_name in decompiled_mods:
                decompiled_mods[online_mod_name]["is_deprecated"] = is_deprecated

                if online_mod_version == decompiled_mods[online_mod_name]["online_version"]:
                    continue

            plugins = extract_mod_metadata(online_mod_name, online_mod_version, download_url)

            write_lock.acquire()
            try:
                if online_mod_name not in decompiled_mods:
                    decompiled_mods[online_mod_name] = {}

                decompiled_mods[online_mod_name]["online_name"] = online_mod_name
                decompiled_mods[online_mod_name]["online_version"] = online_mod_version
                decompiled_mods[online_mod_name]["date"] = date_created
                decompiled_mods[online_mod_name]["is_deprecated"] = is_deprecated

                if "mods" not in decompiled_mods[online_mod_name]:
                    decompiled_mods[online_mod_name]["mods"] = {}

                if plugins is not None:
                    for arguments in plugins:
                        if arguments is not None:
                            mod_guid = arguments[0]
                            mod_name = arguments[1]
                            mod_version = arguments[2]

                            decompiled_mods[online_mod_name]["mods"][mod_guid] = {
                                "name": mod_name,
                                "version": mod_version,
                            }

                with open(decompiled_mods_file_path, "w") as f:
                    json.dump(decompiled_mods, f, indent=4)

            finally:
                write_lock.release()

    with open(decompiled_mods_file_path, "w") as f:
        json.dump(decompiled_mods, f, indent=4)

    logging.info("Fetching Thunderstore done")


def write_extracted_mod_to_file(arguments, online_mod_name, decompiled_mods, write_lock):
    if arguments is not None and len(arguments) == 3:
        mod_guid = arguments[0]
        mod_name = arguments[1]
        mod_version = arguments[2]

        write_lock.acquire()
        try:
            decompiled_mods[online_mod_name]["mods"][mod_guid] = {
                "name": mod_name,
                "version": mod_version,
            }

            with open(decompiled_mods_file_path, "w") as f:
                json.dump(decompiled_mods, f, indent=4)

        finally:
            write_lock.release()


def read_extracted_mod_from_file(read_lock) -> dict:
    read_lock.acquire()
    try:
        return _read_decompiled_mods()
    finally:
        read_lock.release()


def _read_decompiled_mods() -> dict:
    if os.path.isfile(decompiled_mods_file_path):
        with open(decompiled_mods_file_path, "r") as f:
            decompiled_mods: dict = json.load(f)
            return decompiled_mods
    else:
        return {}


def extract_mod_metadata(mod_name, mod_version, download_url):
    logging.info(f"Downloading {mod_name} {mod_version} from {download_url}")
    r = requests.get(download_url)
    plugins = extract_bep_in_plugin(mod_name, mod_version, r)

    for plugin in plugins:
        arguments = str(plugin)[13:-2].replace("\"", "").replace(" ", "").split(",")
        yield arguments


def extract_bep_in_plugin(mod_name, mod_version, r):
    with tempfile.TemporaryDirectory() as decompile_dir:
        with tempfile.TemporaryDirectory() as zip_extract_dir:
            try:
                with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
                    tmpfile.write(r.content)
                    try:
                        shutil.unpack_archive(tmpfile.name, zip_extract_dir, "zip")
                    except Exception as e:
                        logging.error(f"Failed to unpack {tmpfile.name} to {zip_extract_dir}")
                        logging.error(e)
                        return []

                    logging.info(f"Extracting {mod_name} {mod_version}...")
                    for root, subdirs, files in os.walk(zip_extract_dir):
                        for file in files:
                            if file.endswith(".dll"):
                                file_path = os.path.join(root, file)
                                try:
                                    logging.info(f"decompiling    {file_path}...")
                                    os.system(
                                        f"ilspycmd --no-dead-code --no-dead-stores -o \"{decompile_dir}\" \"{file_path}\"")
                                except Exception as e:
                                    pass
            finally:
                os.unlink(tmpfile.name)

        for root, subdirs, files in os.walk(decompile_dir):
            for file in files:
                if file.endswith(".cs"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding='utf8') as f:
                        reader = f.read()
                        for line in reader.splitlines():
                            if line.strip().startswith("[BepInPlugin"):
                                yield line.strip()
