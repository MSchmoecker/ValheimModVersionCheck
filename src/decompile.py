import json
import logging
import os
import shutil
import tempfile
from typing import Iterator, List, Tuple

import requests
from readerwriterlock.rwlock import RWLockRead

from src import hexium, thunderstore
from src.mod import Mod, HEXIUM, THUNDERSTORE

# Bump when metadata extraction changes, so mods can be considered for re-decompilation
# 1: legacy
# 2: quote-aware version split
DECOMPILE_PARSER_VERSION = 2


def fetch_online(host: str, community: str) -> Tuple[bool, List[dict]]:
    if host == THUNDERSTORE:
        return thunderstore.fetch_online(community)
    if host == HEXIUM:
        return hexium.fetch_online(community)
    raise ValueError(f"{host} cannot be decompiled")


def download_mod(host: str, download_url: str) -> requests.Response:
    if host == THUNDERSTORE:
        return thunderstore.download_mod(download_url)
    if host == HEXIUM:
        return hexium.download_mod(download_url)
    raise ValueError(f"{host} cannot be decompiled")


def mods_file_path(host: str, community: str) -> str:
    return os.path.join("data", f"{community}_{host.lower()}_decompiled_mods.json")


def fetch_mods(host: str, community: str, file_lock: RWLockRead):
    logging.info(f"Fetching {host} for {community} ...")
    success, online_mods = fetch_online(host, community)

    if not success:
        return

    write_lock = file_lock.gen_rlock()
    read_lock = file_lock.gen_rlock()
    decompiled_mods = read_extracted_mod_from_file(host, community, read_lock)

    mod_lookup = set()
    for mod in online_mods:
        mod_lookup.add(mod["full_name"])

    for mod in list(decompiled_mods.keys()):
        if mod not in mod_lookup:
            logging.info(
                f"Removing {mod} from decompiled mods, not longer on {host}"
            )
            del decompiled_mods[mod]

    for mod in online_mods:
        online_mod_name = mod["full_name"]
        online_name = mod["name"]
        online_mod_version = mod["versions"][0]["version_number"]
        download_url = mod["versions"][0]["download_url"]
        date_created = mod["versions"][0]["date_created"]
        icon_url = mod["versions"][0]["icon"]
        is_deprecated = mod["is_deprecated"]
        is_modpack = thunderstore.is_modpack(mod)
        url = mod["package_url"]

        if online_name != "r2modman":
            if online_mod_name in decompiled_mods:
                decompiled_mods[online_mod_name]["is_deprecated"] = is_deprecated
                decompiled_mods[online_mod_name]["url"] = url
                decompiled_mods[online_mod_name]["icon_url"] = icon_url
                decompiled_mods[online_mod_name]["is_modpack"] = is_modpack
                decompiled_mods[online_mod_name]["categories"] = mod["categories"]

                if (
                    online_mod_version
                    == decompiled_mods[online_mod_name]["online_version"]
                ):
                    entry = decompiled_mods[online_mod_name]
                    parser_current = (
                        entry.get("parser_version", 0) >= DECOMPILE_PARSER_VERSION
                    )
                    if parser_current or not has_invalid_version(entry):
                        continue

            plugins = extract_mod_metadata(
                host, online_mod_name, online_mod_version, download_url
            )

            write_lock.acquire()
            try:
                if online_mod_name not in decompiled_mods:
                    decompiled_mods[online_mod_name] = {}

                decompiled_mods[online_mod_name]["online_name"] = online_mod_name
                decompiled_mods[online_mod_name]["online_version"] = online_mod_version
                decompiled_mods[online_mod_name]["date"] = date_created
                decompiled_mods[online_mod_name]["is_deprecated"] = is_deprecated
                decompiled_mods[online_mod_name]["url"] = url
                decompiled_mods[online_mod_name]["icon_url"] = icon_url
                decompiled_mods[online_mod_name]["is_modpack"] = is_modpack
                decompiled_mods[online_mod_name]["mods"] = {}
                decompiled_mods[online_mod_name][
                    "parser_version"
                ] = DECOMPILE_PARSER_VERSION

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

                with open(mods_file_path(host, community), "w") as f:
                    json.dump(decompiled_mods, f, indent=4)

            finally:
                write_lock.release()

    write_lock.acquire()

    with open(mods_file_path(host, community), "w") as f:
        json.dump(decompiled_mods, f, indent=4)

    write_lock.release()

    logging.info(f"Fetching {host} for {community} done")


def read_extracted_mod_from_file(host: str, community: str, read_lock) -> dict:
    read_lock.acquire()
    try:
        return _read_decompiled_mods(host, community)
    finally:
        read_lock.release()


def _read_decompiled_mods(host: str, community: str) -> dict:
    try:
        with open(mods_file_path(host, community), "r") as f:
            decompiled_mods: dict = json.load(f)
            return decompiled_mods
    except:
        return {}


def to_mods(decompiled_mods: dict, source: str) -> List[Mod]:
    """The decompiled format is host independent, only the source name differs."""
    mods: List[Mod] = []

    for package in decompiled_mods.values():
        updated = thunderstore.parse_date(package["date"])
        deprecated = package.get("is_deprecated", False)
        is_modpack = package.get("is_modpack", False)
        categories = package.get("categories", [])
        url = package.get("url", "")
        icon_url = package.get("icon_url", "")

        for mod in package["mods"].values():
            try:
                mods.append(Mod(
                    mod["name"],
                    mod["version"],
                    updated,
                    deprecated,
                    is_modpack,
                    source,
                    icon_url,
                    url,
                    categories,
                ))
            except Exception as e:
                logging.error(f"Error adding mod {mod['name']} version {mod['version']} from {source}: {e}")

    return mods


def extract_mod_metadata(host: str, mod_name: str, mod_version: str, download_url: str) -> Iterator[List[str]]:
    logging.info(f"Downloading {mod_name} {mod_version} from {download_url}")
    r = download_mod(host, download_url)
    plugins = extract_bep_in_plugin(mod_name, mod_version, r)

    for plugin in plugins:
        arguments = parse_bep_in_plugin_arguments(str(plugin))
        if arguments is not None:
            yield arguments


def parse_bep_in_plugin_arguments(line):
    # [BepInPlugin("guid", "name", "version")] -- split only on top-level commas
    # so a comma inside the name (e.g. "Foo, Bar") doesn't leak into version.
    start = line.find("(")
    end = line.rfind(")")
    if start == -1 or end == -1 or end < start:
        return None

    inner = line[start + 1 : end]
    arguments = []
    current = []
    in_string = False
    escape = False
    for ch in inner:
        if escape:
            current.append(ch)
            escape = False
        elif ch == "\\":
            escape = True
        elif ch == '"':
            in_string = not in_string
        elif ch == "," and not in_string:
            arguments.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    arguments.append("".join(current).strip())

    if len(arguments) < 3:
        return None

    return arguments[:3]


def extract_bep_in_plugin(mod_name, mod_version, r):
    with tempfile.TemporaryDirectory() as decompile_dir:
        with tempfile.TemporaryDirectory() as zip_extract_dir:
            try:
                with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
                    tmpfile.write(r.content)
                    try:
                        shutil.unpack_archive(tmpfile.name, zip_extract_dir, "zip")
                    except Exception as e:
                        logging.error(
                            f"Failed to unpack {tmpfile.name} to {zip_extract_dir}"
                        )
                        logging.error(e)
                        return []

                    logging.info(f"Extracting {mod_name} {mod_version}...")
                    for root, subdirs, files in os.walk(zip_extract_dir):
                        for file in files:
                            if file.endswith(".dll"):
                                file_path = os.path.join(root, file)
                                try:
                                    logging.info(f"decompiling {file_path}...")
                                    os.system(
                                        f'ilspycmd --no-dead-code --no-dead-stores -o "{decompile_dir}" "{file_path}"'
                                    )
                                except Exception as e:
                                    pass
            finally:
                os.unlink(tmpfile.name)

        for root, subdirs, files in os.walk(decompile_dir):
            for file in files:
                if file.endswith(".cs"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf8") as f:
                        reader = f.read()
                        for line in reader.splitlines():
                            if line.strip().startswith("[BepInPlugin"):
                                yield line.strip()

def has_invalid_version(package: dict) -> bool:
    # A wrongly parsed version lacks a dot (a real one is like "1.0.3").
    for mod in package.get("mods", {}).values():
        if "." not in mod.get("version", ""):
            return True
    return False
