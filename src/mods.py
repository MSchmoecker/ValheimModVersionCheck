import copy
import datetime
import logging
import threading
from typing import Dict, List, Tuple

from readerwriterlock.rwlock import RWLockRead

from src import nexus, thunderstore, hexium, decompile, env, config
from src.mod import Mod, HEXIUM, THUNDERSTORE, NEXUS


class ModList:
    last_online_fetched: datetime = None

    def __init__(self, file_lock: RWLockRead):
        self._mods_online: Dict[str, Dict[str, Mod]] = {}
        self._mods_guid: Dict[str, Dict[str, Mod]] = {}
        self.decompile_thread = None
        self.file_lock = file_lock
        self.read_lock = file_lock.gen_rlock()
        self.write_lock = file_lock.gen_wlock()

    def get_online_mods(self, community: str) -> Dict[str, Mod]:
        return self._get_mods(self._mods_online, community)

    def get_online_mods_by_guid(self, community: str) -> Dict[str, Mod]:
        return self._get_mods(self._mods_guid, community)

    def _get_mods(self, index: Dict[str, Dict[str, Mod]], community: str) -> Dict[str, Mod]:
        self.read_lock.acquire()
        try:
            return index[community]
        except:
            return {}
        finally:
            self.read_lock.release()

    def _add_online_mod(self, community: str, mod: Mod):
        self.write_lock.acquire()

        if community not in self._mods_online:
            self._mods_online[community] = {}

        self._mods_online[community][mod.clean_name] = mod

        self.write_lock.release()

    def _add_guid_mod(self, community: str, mod: Mod):
        self.write_lock.acquire()

        if community not in self._mods_guid:
            self._mods_guid[community] = {}

        self._mods_guid[community][mod.guid] = mod

        self.write_lock.release()

    def fetch_mods(self):
        refresh_time = datetime.timedelta(minutes=5)

        if self.last_online_fetched is not None and self.last_online_fetched >= datetime.datetime.now() - refresh_time:
            logging.info("Skipping online fetch, last fetch was less than 5 minutes ago")
            return

        self.last_online_fetched = datetime.datetime.now()

        if env.DECOMPILE_MODS:
            self.run_decompile_thread()
            return

        for game in config.get_games():
            self.update_mod_list(game)

    @staticmethod
    def _decompilable_hosts(game: config.GameConfig) -> List[Tuple[str, str]]:
        """(host, community) pairs of the hosts serving the Thunderstore API, in preference order."""
        hosts: List[Tuple[str, str]] = []

        if game.thunderstore:
            hosts.append((THUNDERSTORE, game.thunderstore))
        if game.hexium:
            hosts.append((HEXIUM, game.hexium))

        return hosts

    @staticmethod
    def _fetch_online_mods(host: str, community: str) -> List[Mod]:
        if host == THUNDERSTORE:
            return thunderstore.to_mods(community)
        if host == HEXIUM:
            return hexium.to_mods(community)
        raise ValueError(f"{host} is not a Thunderstore API host")

    def _host_mods(self, host: str, community: str, game_name: str) -> List[Mod]:
        # Decompiled metadata is always used when present, it is more reliable than the package names.
        decompiled = decompile.read_extracted_mod_from_file(host, community, self.read_lock)
        mods = decompile.to_mods(decompiled, host)

        if not env.DECOMPILE_MODS:
            logging.info(f"Fetching {host} for {game_name} ...")
            mods += self._fetch_online_mods(host, community)

        return mods

    def update_mod_list(self, game: config.GameConfig):
        # Order matters: equally ranked mods keep this order through the stable sort below.
        mods: List[Mod] = []

        for host, community in self._decompilable_hosts(game):
            mods += self._host_mods(host, community, game.name)

        if game.nexus:
            logging.info(f"Fetching {NEXUS} for {game.name} ...")
            mods += nexus.to_mods(game.nexus)

        self.index_mods(game.name, mods)

    def index_mods(self, game_name: str, mods: List[Mod]):
        logging.info(f"Adding mods for {game_name} ...")

        mods_by_name: Dict[str, List[Mod]] = {}
        mods_by_guid: Dict[str, List[Mod]] = {}

        for mod in mods:
            mods_by_name.setdefault(mod.clean_name, []).append(mod)
            if mod.guid:
                mods_by_guid.setdefault(mod.guid, []).append(mod)

        for candidates in mods_by_name.values():
            self._add_online_mod(game_name, self._merge_candidates(candidates))

        for candidates in mods_by_guid.values():
            self._add_guid_mod(game_name, self._merge_candidates(candidates))

        logging.info(f"All {game_name} mods updated")

    @staticmethod
    def _merge_candidates(candidates: List[Mod]) -> Mod:
        """The best of the candidates, carrying the urls of every candidate worth linking."""
        ordered = sorted(candidates)
        best_candidate = copy.copy(ordered[0])
        # a host contributes both its decompiled and its online entry, which share a url
        urls = [mod.urls[0] for mod in ordered if mod.use_as_url(ordered[0])]
        best_candidate.urls = list(dict.fromkeys(urls))
        return best_candidate

    def get_decompiled_mods(self, game_name: str) -> dict:
        mods = {}

        for game in config.get_games():
            if game.name != game_name:
                continue

            for host, community in self._decompilable_hosts(game):
                mods.update(decompile.read_extracted_mod_from_file(host, community, self.read_lock))

        return mods

    def decompile_mods(self):
        for game in config.get_games():
            for host, community in self._decompilable_hosts(game):
                decompile.fetch_mods(host, community, self.file_lock)
            self.update_mod_list(game)

    def run_decompile_thread(self):
        if self.decompile_thread is None or not self.decompile_thread.is_alive():
            logging.info("Start decompile thread")
            self.decompile_thread = threading.Thread(target=self.decompile_mods, name="DecompileThread", daemon=True)
            self.decompile_thread.start()
        else:
            logging.info("Decompile thread is already running")
