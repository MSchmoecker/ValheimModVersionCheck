import datetime
import logging
from typing import Dict, Optional
from packaging import version
from src import Mod, clean_name


class ParsedLog:
    mods = {}
    valheim_version: Optional[version.Version] = None
    bepinex_version: Optional[version.Version] = None
    bepinex_thunderstore_version: Optional[version.Version] = None


def parse_version(prefix: str, anywhere: bool, line: str) -> Optional[version.Version]:
    if anywhere and prefix in line:
        version_string = line.split(prefix)[1].strip().split(" ")[0]
    elif line.startswith(prefix):
        version_string = line.split(prefix)[1].strip().split(" ")[0]
    else:
        version_string = None

    if version_string:
        return version.parse(version_string)

    return None


def parse_local(local_text, is_logfile: bool) -> ParsedLog:
    parsed_log = ParsedLog()

    lines = local_text.splitlines()
    for i, line in enumerate(lines):
        if not parsed_log.valheim_version and line.startswith("[Info   : Unity Log] "):
            search = ": Valheim version: "
            parsed_log.valheim_version = parse_version(search, True, line)

        if not parsed_log.bepinex_version:
            search = "[Message:   BepInEx] BepInEx"
            parsed_log.bepinex_version = parse_version(search, False, line)

        if not parsed_log.bepinex_thunderstore_version:
            search = "[Message:   BepInEx] User is running BepInExPack Valheim version"
            parsed_log.bepinex_thunderstore_version = parse_version(search, False, line)

        if is_logfile:
            if not line.startswith("[Info   :   BepInEx] Loading ["):
                continue
            line = line[line.index("[", 1) + 1:line.index("]", 20)]

        mod_name = clean_name("".join(line.split(" ")[:-1])).lower()
        mod_original_name = "".join(line.split(" ")[:-1])
        mod_version = "".join(line.split(" ")[-1])

        parsed_log.mods[mod_name] = {
            "original_name": mod_original_name,
            "version": version.parse(mod_version)
        }

    return parsed_log


def compare_mods(mods_local, mods_online: Dict[str, Mod]):
    time_threshold = datetime.datetime.now() - datetime.timedelta(days=30 * 12)
    result = ""

    for mod in sorted(mods_local, key=lambda x: mods_local[x]["original_name"].lower()):
        original_name = mods_local[mod]["original_name"]
        mod_version = mods_local[mod]["version"]

        if mod not in mods_online.keys():
            logging.info(f"{original_name} not found!")
            continue

        outdated = mod_version < mods_online[mod].version
        old = mods_online[mod].updated < time_threshold
        deprecated = mods_online[mod].deprecated

        if outdated or old or deprecated:
            result += f"{original_name} {mod_version}\n"

        if deprecated:
            result += f"\tis deprecated\n"

        if outdated:
            result += f"\tis likely outdated, version {mods_online[mod].version} exists:\n"
            for url in mods_online[mod].urls:
                result += f"\t\t{url}\n"

        if old:
            result += f"\tis older than one year (uploaded {mods_online[mod].updated.strftime('%Y-%m-%d')})\n"

        if mod_version > mods_online[mod].version:
            continue
            result += f"{original_name} is newer"
            result += f"\t{mod_version} -> {mods_online[mod].version}\n"

    return result


def fetch_errors(log):
    errors = ""
    is_in_error = False
    was_in_warning = False

    for i, line in enumerate(log.splitlines()):
        if line == "":
            if is_in_error:
                errors += "\n"
            is_in_error = False
            continue

        if line.startswith("[Info") or line.startswith("[Debug") or line.startswith("[Message"):
            if is_in_error:
                errors += "\n"
            is_in_error = False
            was_in_warning = False

        if is_in_error or line.startswith("[Error") or line.startswith("[Fatal") or "Exception in ZRpc::HandlePackage:" in line:
            if was_in_warning or not is_in_error:
                errors += "\n"
                was_in_warning = False
            errors += f"{line}\n"
            is_in_error = True

        if line.startswith("[Warning"):
            errors += f"{line}\n"
            was_in_warning = True

    return errors.replace("\n\n\n", "\n\n")


def merge_errors(errors) -> str:
    result = ""
    max_length = 50
    lines = errors.splitlines()
    skip = 0

    for i1, error in enumerate(lines):
        if skip > 0:
            skip -= 1
            continue
        for i2, line in enumerate(lines[i1 + 1:i1 + max_length]):
            if error == line:
                end_pos = i1 + 1 + i2
                length = end_pos - i1
                block1 = lines[i1:end_pos]
                block2 = lines[end_pos:end_pos + length]
                duplicates = 1

                while block1 == block2:
                    end_pos += length
                    block2 = lines[end_pos:end_pos + length]
                    duplicates += 1

                if duplicates > 1 and len(block1) * duplicates >= 3:
                    header = f"----- {duplicates}x -----"
                    result += "\n" + header + "\n"
                    result += "\n".join(block1).strip() + "\n"
                    result += "-" * len(header) + "\n\n"
                    skip = length * duplicates - 1
                    break
        if skip > 0:
            continue
        result += error + "\n"

    return result.replace("\n\n\n", "\n\n")
