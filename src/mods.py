import datetime
import logging
import threading
from typing import Dict

from readerwriterlock.rwlock import RWLockRead

from src import nexus, thunderstore, clean_name, decompile, env
from packaging import version


class Mod:
    name: str
    clean_name: str
    version: version
    updated: datetime.datetime

    def __init__(self, name: str, mod_version: str, updated: datetime.datetime):
        self.name = name
        self.clean_name = clean_name(name).lower()
        self.version = version.parse(mod_version)
        self.updated = updated


class ModList:
    mods_online: Dict[str, Mod] = {}
    last_online_fetched: datetime = None

    def __init__(self, file_lock: RWLockRead):
        self.decompile_thread = None
        self.file_lock = file_lock
        self.read_lock = file_lock.gen_rlock()

    @staticmethod
    def parse_thunder_created_date(date):
        return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")

    @staticmethod
    def parse_nexus_created_date(date):
        return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%f%z").replace(tzinfo=None)

    def _try_add_online_mod(self, mod: Mod, soft_add=False):
        if mod.clean_name in self.mods_online:
            if not soft_add and mod.version > self.mods_online[mod.clean_name].version:
                self.mods_online[mod.clean_name] = mod
            elif mod.version == self.mods_online[mod.clean_name].version:
                self.mods_online[mod.clean_name].updated = min(mod.updated, self.mods_online[mod.clean_name].updated)
        else:
            self.mods_online[mod.clean_name] = mod

    def fetch_mods(self):
        refresh_time = datetime.timedelta(minutes=5)

        if self.last_online_fetched is not None and self.last_online_fetched >= datetime.datetime.now() - refresh_time:
            logging.info("Skipping online fetch, last fetch was less than 5 minutes ago")
            return

        self.last_online_fetched = datetime.datetime.now()

        if env.DECOMPILE_THUNDERSTORE_MODS:
            if self.decompile_thread is None or not self.decompile_thread.is_alive():
                logging.info("Start decompile thread")
                self.decompile_thread = threading.Thread(target=decompile.fetch_mods, name="Decompile",
                                                         args=(self.file_lock,), daemon=True)
                self.decompile_thread.start()
            else:
                logging.info("Decompile thread is already running")

            thunder_mods = []
        else:
            logging.info("Fetching Thunderstore ...")
            thunder_mods = thunderstore.fetch_online()

        logging.info("Fetching Nexus ...")
        nexus_mods = nexus.fetch_online()

        logging.info("Adding mods ...")

        decompiled_mods = decompile.read_extracted_mod_from_file(self.read_lock)
        for online_mod_key in decompiled_mods:
            online_mod = decompiled_mods[online_mod_key]
            mod_updated = self.parse_thunder_created_date(online_mod["date"])

            for mod in online_mod["mods"]:
                mod_name = online_mod["mods"][mod]["name"]
                mod_version = online_mod["mods"][mod]["version"]
                self._try_add_online_mod(Mod(mod_name, mod_version, mod_updated))

        for mod in thunder_mods:
            mod_name = mod["name"]
            mod_version = mod["versions"][0]["version_number"]
            mod_updated = self.parse_thunder_created_date(mod["versions"][0]["date_created"])
            self._try_add_online_mod(Mod(mod_name, mod_version, mod_updated))

        for mod in nexus_mods.values():
            if mod is None or mod["status"] != "published":
                continue
            mod_name = mod["name"]
            mod_version = mod["version"]
            mod_updated = self.parse_nexus_created_date(mod["updated_time"])
            self._try_add_online_mod(Mod(mod_name, mod_version, mod_updated), True)

        logging.info("All mods updated")
        return self.mods_online
