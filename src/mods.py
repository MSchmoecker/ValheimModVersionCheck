import datetime
import logging
import threading
from typing import Dict, List

from readerwriterlock.rwlock import RWLockRead

from src import nexus, thunderstore, clean_name, decompile, env
from packaging import version


class Mod:
    name: str
    clean_name: str
    version: version
    updated: datetime.datetime
    deprecated: bool
    urls: List[str]

    def __init__(self, name: str, mod_version: str, updated: datetime.datetime, deprecated: bool, url: str):
        self.name = name
        self.clean_name = clean_name(name).lower()
        self.version = version.parse(mod_version)
        self.updated = updated
        self.deprecated = deprecated
        self.urls = [url]


class ModList:
    _mods_online: Dict[str, Mod] = {}
    last_online_fetched: datetime = None

    def __init__(self, file_lock: RWLockRead):
        self.decompile_thread = None
        self.file_lock = file_lock
        self.read_lock = file_lock.gen_rlock()
        self.write_lock = file_lock.gen_wlock()

    def get_online_mods(self) -> Dict[str, Mod]:
        self.read_lock.acquire()
        try:
            return self._mods_online
        finally:
            self.read_lock.release()

    @staticmethod
    def parse_thunder_created_date(date):
        return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")

    @staticmethod
    def parse_nexus_created_date(date):
        return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%f%z").replace(tzinfo=None)

    def _can_add_mod(self, mod: Mod, soft_add=False):
        if mod.clean_name not in self._mods_online:
            return True

        online_mod = self._mods_online[mod.clean_name]

        if mod.version > online_mod.version and not soft_add and not mod.deprecated:
            return True

        if mod.version == online_mod.version and mod.updated < online_mod.updated:
            return True

        return False

    def _try_add_online_mod(self, mod: Mod, soft_add=False):
        self.write_lock.acquire()

        if mod.clean_name in self._mods_online:
            same_version = self._mods_online[mod.clean_name].version == mod.version
            if same_version:
                urls = self._mods_online[mod.clean_name].urls + mod.urls
                distinct_urls = list(set(urls))
                distinct_urls.sort()
                self._mods_online[mod.clean_name].urls = distinct_urls
                mod.urls = distinct_urls

        if self._can_add_mod(mod, soft_add):
            self._mods_online[mod.clean_name] = mod

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

        self.update_mod_list()

    def update_mod_list(self):
        if not env.DECOMPILE_THUNDERSTORE_MODS:
            logging.info("Fetching Thunderstore ...")
            thunder_mods = thunderstore.fetch_online()
        else:
            thunder_mods = []

        logging.info("Fetching Nexus ...")
        nexus_mods = nexus.fetch_online()

        logging.info("Adding mods ...")

        decompiled_mods = decompile.read_extracted_mod_from_file(self.read_lock)

        for online_mod_key in decompiled_mods:
            online_mod = decompiled_mods[online_mod_key]
            mod_updated = self.parse_thunder_created_date(online_mod["date"])
            deprecated = online_mod["is_deprecated"] if "is_deprecated" in online_mod else False

            for mod_key in online_mod["mods"]:
                mod = online_mod["mods"][mod_key]
                mod_name = mod["name"]
                mod_version = mod["version"]
                url = online_mod["url"] if "url" in online_mod else ""
                self._try_add_online_mod(Mod(mod_name, mod_version, mod_updated, deprecated, url))

        for mod in thunder_mods:
            mod_name = mod["name"]
            mod_version = mod["versions"][0]["version_number"]
            mod_updated = self.parse_thunder_created_date(mod["versions"][0]["date_created"])
            deprecated = mod["is_deprecated"]
            url = mod["package_url"]
            self._try_add_online_mod(Mod(mod_name, mod_version, mod_updated, deprecated, url), True)

        for mod in nexus_mods.values():
            if mod is None or mod["status"] != "published":
                continue
            mod_name = mod["name"]
            mod_version = mod["version"]
            mod_updated = self.parse_nexus_created_date(mod["updated_time"])
            url = f"https://www.nexusmods.com/valheim/mods/{mod['mod_id']}"
            self._try_add_online_mod(Mod(mod_name, mod_version, mod_updated, False, url), True)

        logging.info("All mods updated")

    def get_decompiled_mods(self):
        return decompile.read_extracted_mod_from_file(self.read_lock)

    def decompile_mods(self):
        decompile.fetch_mods(self.file_lock)
        self.update_mod_list()

    def run_decompile_thread(self):
        if self.decompile_thread is None or not self.decompile_thread.is_alive():
            logging.info("Start decompile thread")
            self.decompile_thread = threading.Thread(target=self.decompile_mods, name="DecompileThread", daemon=True)
            self.decompile_thread.start()
        else:
            logging.info("Decompile thread is already running")
