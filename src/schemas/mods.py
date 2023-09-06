import datetime
from typing import Dict, List

from pydantic import BaseModel, RootModel, field_validator


class Mod(BaseModel):
    name: str
    version: str


class ModMetadata(BaseModel):
    url: str
    online_name: str
    online_version: str
    icon_url: str
    is_deprecated: bool
    date: datetime.datetime
    mods: Dict[str, Mod]


class ModList(RootModel):
    root: Dict[str, ModMetadata]


class BepInExMod(BaseModel):
    name: str
    clean_name: str
    version: str
    updated: datetime.datetime
    deprecated: bool
    urls: List[str]
    icon_url: str

    @field_validator("version", mode="before")
    def validate_uuids(cls, value):
        if value:
            return str(value)
        return ""


class BepInExModList(RootModel):
    root: Dict[str, BepInExMod]
