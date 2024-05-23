import datetime
import logging
import threading
from typing import Dict, List, Optional

from readerwriterlock.rwlock import RWLockRead

from src import nexus, thunderstore, clean_name, decompile, env, config
from packaging import version


class Mod:
    name: str
    clean_name: str
    icon_url: str
    version: version
    updated: datetime.datetime
    deprecated: bool
    is_modpack: bool
    source: str
    urls: List[str]

    def __init__(self, name: str, mod_version: str, updated: datetime.datetime, deprecated: bool, is_modpack: bool, source: str, icon_url: str, url: str):
        self.name = name
        self.clean_name = clean_name(name).lower()
        self.version = version.parse(mod_version)
        self.updated = updated
        self.deprecated = deprecated
        self.is_modpack = is_modpack
        self.source = source
        self.urls = [url]
        self.icon_url = icon_url or ""

    def __lt__(self, other):
        # prefer Thunderstore
        if self.source == "Thunderstore" and other.source == "Nexus":
            return True
        if self.source == "Nexus" and other.source == "Thunderstore":
            return False

        # prefer non-modpacks
        if not self.is_modpack and other.is_modpack:
            return True
        if self.is_modpack and not other.is_modpack:
            return False

        # prefer higher version
        if self.version > other.version:
            return True
        if self.version < other.version:
            return False

        # prefer original uploads over possible reuploads
        return self.updated < other.updated


class ModList:
    _mods_online: Dict[str, Dict[str, Mod]] = {}
    last_online_fetched: datetime = None

    def __init__(self, file_lock: RWLockRead):
        self.decompile_thread = None
        self.file_lock = file_lock
        self.read_lock = file_lock.gen_rlock()
        self.write_lock = file_lock.gen_wlock()

    def get_online_mods(self, community: str) -> Dict[str, Mod]:
        self.read_lock.acquire()
        try:
            return self._mods_online[community]
        except:
            return {}
        finally:
            self.read_lock.release()

    @staticmethod
    def parse_thunder_created_date(date):
        return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")

    @staticmethod
    def parse_nexus_created_date(date):
        return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%f%z").replace(tzinfo=None)

    def _add_online_mod(self, community: str, mod: Mod):
        self.write_lock.acquire()

        if community not in self._mods_online:
            self._mods_online[community] = {}

        self._mods_online[community][mod.clean_name] = mod

        self.write_lock.release()

    def fetch_mods(self):
        refresh_time = datetime.timedelta(minutes=5)

        if self.last_online_fetched is not None and self.last_online_fetched >= datetime.datetime.now() - refresh_time:
            logging.info("Skipping online fetch, last fetch was less than 5 minutes ago")
            return

        self.last_online_fetched = datetime.datetime.now()

        if env.DECOMPILE_THUNDERSTORE_MODS:
            self.run_decompile_thread()
            return

        for game in config.get_games():
            self.update_mod_list(game)

    def update_mod_list(self, game: config.GameConfig):
        if game.thunderstore and not env.DECOMPILE_THUNDERSTORE_MODS:
            logging.info(f"Fetching Thunderstore for {game.name} ...")
            success, thunder_mods = thunderstore.fetch_online(game.thunderstore)
        else:
            thunder_mods = []

        if game.nexus:
            logging.info(f"Fetching Nexus for {game.name} ...")
            nexus_mods = nexus.fetch_online(game.nexus)
        else:
            nexus_mods = {}

        logging.info(f"Adding mods for {game.name} ...")

        if game.thunderstore:
            decompiled_mods = decompile.read_extracted_mod_from_file(game.thunderstore, self.read_lock)
        else:
            decompiled_mods = {}

        mods_sources: Dict[str, List[Mod]] = {}

        for online_mod_key in decompiled_mods:
            online_mod = decompiled_mods[online_mod_key]
            mod_updated = self.parse_thunder_created_date(online_mod["date"])
            deprecated = online_mod["is_deprecated"] if "is_deprecated" in online_mod else False
            is_modpack = online_mod["is_modpack"] if "is_modpack" in online_mod else False

            for mod_key in online_mod["mods"]:
                mod = online_mod["mods"][mod_key]
                mod_name = mod["name"]
                mod_version = mod["version"]
                url = online_mod["url"] if "url" in online_mod else ""
                icon_url = online_mod["icon_url"] if "icon_url" in online_mod else ""

                clean = clean_name(mod_name).lower()
                if clean not in mods_sources:
                    mods_sources[clean] = []
                mods_sources[clean].append(Mod(mod_name, mod_version, mod_updated, deprecated, is_modpack, "Thunderstore", icon_url, url))

        for mod in thunder_mods:
            mod_name = mod["name"]
            mod_version = mod["versions"][0]["version_number"]
            mod_updated = self.parse_thunder_created_date(mod["versions"][0]["date_created"])
            deprecated = mod["is_deprecated"]
            url = mod["package_url"]
            icon_url = mod["versions"][0]["icon"]
            is_modpack = "Modpacks" in mod["categories"] or "modpack" in mod_name.lower() or len(mod["versions"][0]["dependencies"]) >= 5

            clean = clean_name(mod_name).lower()
            if clean not in mods_sources:
                mods_sources[clean] = []
            mods_sources[clean].append(Mod(mod_name, mod_version, mod_updated, deprecated, is_modpack, "Thunderstore", icon_url, url))

        for mod in nexus_mods.values():
            if mod is None or mod["status"] != "published":
                continue
            mod_name = mod["name"]
            mod_version = mod["version"]
            mod_updated = self.parse_nexus_created_date(mod["updated_time"])
            url = f"https://www.nexusmods.com/{game.nexus}/mods/{mod['mod_id']}"
            icon_url = mod["picture_url"]

            clean = clean_name(mod_name).lower()
            if clean not in mods_sources:
                mods_sources[clean] = []
            mods_sources[clean].append(Mod(mod_name, mod_version, mod_updated, False, False, "Nexus", icon_url, url))

        for mod in mods_sources:
            ordered = sorted(mods_sources[mod])
            main = ordered[0]
            main.urls = [m.urls[0] for m in ordered if m == main or not (m.deprecated or m.is_modpack)]
            self._add_online_mod(game.name, main)

        logging.info(f"All {game.name} mods updated")

    def get_decompiled_mods(self, community: str):
        return decompile.read_extracted_mod_from_file(community, self.read_lock)

    def decompile_mods(self):
        for game in config.get_games():
            if game.thunderstore:
                decompile.fetch_mods(game.thunderstore, self.file_lock)
                self.update_mod_list(game)

    def run_decompile_thread(self):
        if self.decompile_thread is None or not self.decompile_thread.is_alive():
            logging.info("Start decompile thread")
            self.decompile_thread = threading.Thread(target=self.decompile_mods, name="DecompileThread", daemon=True)
            self.decompile_thread.start()
        else:
            logging.info("Decompile thread is already running")
