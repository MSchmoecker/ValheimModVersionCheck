import datetime
import logging
from typing import Dict
from src import nexus, thunderstore, clean_name
from packaging import version


class Mod:
    name: str
    clean_name: str
    version: version
    updated: datetime.datetime

    def __init__(self, name: str, version: str, updated: datetime.datetime):
        self.name = name
        self.clean_name = clean_name(name).lower()
        self.version = version
        self.updated = updated


class ModList:
    mods_online: Dict[str, Mod] = {}
    last_online_fetched: datetime = None

    @staticmethod
    def parse_thunder_created_date(date):
        return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ")

    @staticmethod
    def parse_nexus_created_date(date):
        return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%f%z").replace(tzinfo=None)

    def _try_add_online_mod(self, mod: Mod):
        if mod.clean_name in self.mods_online:
            if mod.version > self.mods_online[mod.clean_name].version:
                self.mods_online[mod.clean_name] = mod
        else:
            self.mods_online[mod.clean_name] = mod

    def fetch_mods(self):
        refresh_time = datetime.timedelta(minutes=5)

        if self.last_online_fetched is not None and self.last_online_fetched >= datetime.datetime.now() - refresh_time:
            logging.info("Skipping online fetch, last fetch was less than 5 minutes ago")
            return

        self.last_online_fetched = datetime.datetime.now()

        logging.info("Fetching Thunderstore ...")
        thunder_mods = thunderstore.fetch_online()

        logging.info("Fetching Nexus ...")
        nexus_mods = nexus.fetch_online()

        logging.info("Adding mods ...")

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
            self._try_add_online_mod(Mod(mod_name, mod_version, mod_updated))

        logging.info("All mods updated")
        return self.mods_online
