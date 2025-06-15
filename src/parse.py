import datetime
import logging
import re
from typing import Dict, Optional
from packaging import version
from src import Mod, clean_name


class ParsedLog:
    def __init__(self):
        self.mods = {}
        self.patchers = {}
        self.valheim_version: Optional[version.Version] = None
        self.bepinex_version: Optional[version.Version] = None
        self.bepinex_thunderstore_version: Optional[version.Version] = None


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


def parse_mod_load(line: str, parsed_log: ParsedLog):
    if not line.startswith("[Info   :   BepInEx] Loading ["):
        return
    line = line[line.index("[", 1) + 1:line.index("]", 20)]

    mod_name = clean_name("".join(line.split(" ")[:-1])).lower()
    mod_original_name = "".join(line.split(" ")[:-1])
    mod_version = "".join(line.split(" ")[-1])

    parsed_log.mods[mod_name] = {
        "original_name": mod_original_name,
        "version": version.parse(mod_version)
    }


def parse_patcher_load(line: str, parsed_log: ParsedLog):
    if not re.match(r"\[Info   :   BepInEx] Loaded \d+ patcher method from \[.*]", line):
        return
    line = line[line.index("[", 1) + 1:line.index("]", 20)]

    patcher_name = clean_name("".join(line.split(" ")[:-1]))
    patcher_version = "".join(line.split(" ")[-1])

    parsed_log.patchers[patcher_name] = {
        "name": patcher_name,
        "version": version.parse(patcher_version)
    }


def parse_local(local_text) -> ParsedLog:
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

        parse_mod_load(line, parsed_log)
        parse_patcher_load(line, parsed_log)

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


def parse_errors(log: str, context_before=4, context_after=0):
    lines = log.splitlines()
    line_types = ["Normal"] * len(lines)

    for i, line in enumerate(lines):
        if line.startswith("[Error") or line.startswith("[Fatal") or "Exception in ZRpc::HandlePackage:" in line:
            line_types[i] = "Error"
        elif line.startswith("[Warning"):
            line_types[i] = "Warning"
        elif line.startswith("[Info") or line.startswith("[Debug") or line.startswith("[Message") or line.strip() == "":
            line_types[i] = "Normal"
        elif i > 0 and line_types[i - 1] == "Error":
            line_types[i] = "Error"
            lines[i] = "  " + lines[i]
        elif i > 0 and line_types[i - 1] == "Warning":
            line_types[i] = "Warning"
            lines[i] = "  " + lines[i]

    for i, line_type in enumerate(line_types):
        if line_type == "Error" or line_type == "Warning":
            for j in range(max(0, i - context_before), i):
                if line_types[j] == "Normal":
                    line_types[j] = "Context"
            for j in range(i + 1, min(len(lines), i + 1 + context_after)):
                if line_types[j] == "Normal":
                    line_types[j] = "Context"

    errors = ""
    for i, line in enumerate(lines):
        next_is_error = i < len(lines) - 1 and line_types[i + 1] == "Error"
        next_is_not_error = i < len(lines) - 1 and line_types[i + 1] != "Error"
        prefix = f"{str(i + 1).rjust(4)} | "

        if line_types[i] == "Error":
            errors += f"{prefix}{line}\n"
        elif line_types[i] == "Warning":
            errors += f"{prefix}{line}\n"
        elif line_types[i] == "Context" and lines[i].strip() != "":
            errors += f"{prefix}{line}\n"
        if line_types[i] == "Error" and next_is_not_error:
            errors += "\n"
        if line_types[i] != "Error" and next_is_error:
            errors += "\n"

    return errors.replace("\n\n\n", "\n\n").strip("\n")

def merge_errors(errors: str) -> str:
    result = ""
    max_length = 50
    lines = errors.splitlines()
    skip = 0

    for i1, error in enumerate(lines):
        if skip > 0:
            skip -= 1
            continue
        for i2, line in enumerate(lines[i1 + 1:i1 + max_length]):
            if error[4:] == line[4:]:
                end_pos = i1 + 1 + i2
                length = end_pos - i1
                block1 = lines[i1:end_pos]
                block2 = lines[end_pos:end_pos + length]
                block1_cmp = [l[4:] for l in block1]
                block2_cmp = [l[4:] for l in block2]
                duplicates = 1

                while block1_cmp == block2_cmp:
                    end_pos += length
                    block2 = lines[end_pos:end_pos + length]
                    block2_cmp = [l[4:] for l in block2]
                    duplicates += 1

                if duplicates > 1 and len(block1) * duplicates >= 3:
                    header = f"----- {duplicates}x -----"
                    result += "\n" + header + "\n"
                    result += "\n".join(block1).strip("\n") + "\n"
                    result += "-" * len(header) + "\n\n"
                    skip = length * duplicates - 1
                    break
        if skip > 0:
            continue
        result += error + "\n"

    return result.replace("\n\n\n", "\n\n")
