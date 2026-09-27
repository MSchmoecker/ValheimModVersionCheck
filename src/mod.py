import datetime
from typing import List

from src.modnames import clean_name
from src.version import Version

THUNDERSTORE = "Thunderstore"
HEXIUM = "Hexium"
NEXUS = "Nexus"

# Thunderstore and Hexium rank equally: both can be decompiled, so their metadata is trustworthy.
# A tie between them is broken by the order the sources are fetched in, see ModList.update_mod_list.
# Nexus ranks lower, its names and versions cannot be verified.
SOURCE_RANK = {THUNDERSTORE: 0, HEXIUM: 0, NEXUS: 1}


class Mod:
    name: str
    clean_name: str
    icon_url: str
    version: Version
    updated: datetime.datetime
    deprecated: bool
    is_modpack: bool
    source: str
    urls: List[str]
    categories: List[str]

    def __init__(self, name: str, mod_version: str, updated: datetime.datetime, deprecated: bool, is_modpack: bool, source: str, icon_url: str, url: str, categories: List[str]):
        self.name = name
        self.clean_name = clean_name(name).lower()
        self.version = Version(mod_version)
        self.updated = updated
        self.deprecated = deprecated
        self.is_modpack = is_modpack
        self.source = source
        self.urls = [url]
        self.icon_url = icon_url or ""
        self.categories = categories

    def __lt__(self, other):
        # prefer sources that can be verified by decompiling
        if SOURCE_RANK[self.source] != SOURCE_RANK[other.source]:
            return SOURCE_RANK[self.source] < SOURCE_RANK[other.source]

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

    def use_as_url(self, best_candidate):
        if self == best_candidate:
            return True
        if self.deprecated or self.is_modpack:
            return False
        return self.version >= best_candidate.version
