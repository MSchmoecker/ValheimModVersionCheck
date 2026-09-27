import datetime

import pytest
from readerwriterlock.rwlock import RWLockRead

from src.config import GameConfig
from src.mod import Mod, THUNDERSTORE, HEXIUM, NEXUS
from src.mods import ModList
from src.parse import parse_local, compare_mods

GAME = "valheim"


def game_config():
    return GameConfig(name=GAME, bepinex=[], report_old_mods=False)


def online_mod(name, version, guid="", source=THUNDERSTORE, url=None):
    url = url or f"https://mods/{name}"
    return Mod(guid, name, version, datetime.datetime.now(), False, False, source, "", url, [])


def indexed(*mods):
    """The two indexes the bot looks up, built by the real ModList code."""
    modlist = ModList(RWLockRead())
    modlist.index_mods(GAME, list(mods))
    return modlist.get_online_mods(GAME), modlist.get_online_mods_by_guid(GAME)


def compare(line, *mods):
    by_name, by_guid = indexed(*mods)
    return compare_mods(parse_local(line).mods, by_name, by_guid, game_config())


@pytest.mark.parametrize("line, name, version, guid", [
    # older games log no guid at all
    ("[Info   :   BepInEx] Loading [Some Old Mod 1.0.0]", "SomeOldMod", "1.0.0", ""),
    ("[Info   :   BepInEx] Loading [Jotunn 2.20.0]", "Jotunn", "2.20.0", ""),
    # newer ones append the BepInPlugin guid
    ("[Info   :   BepInEx] Loading [AzuAutoStore 3.1.6] (Azumatt.AzuAutoStore)", "AzuAutoStore", "3.1.6", "Azumatt.AzuAutoStore"),
    ("[Info   :   BepInEx] Loading [Spawn That! 1.2.3] (asharppen.valheim.spawn_that)", "SpawnThat!", "1.2.3", "asharppen.valheim.spawn_that"),
])
def test_parses_mod_load_with_and_without_guid(line, name, version, guid):
    entry = next(iter(parse_local(line).mods.values()))

    assert entry["original_name"] == name
    assert str(entry["version"]) == version
    assert entry["guid"] == guid


def test_ignores_a_load_line_without_a_version():
    assert parse_local("[Info   :   BepInEx] Loading [NoVersion]").mods == {}


def test_guid_matches_a_mod_whose_online_name_differs():
    result = compare(
        "[Info   :   BepInEx] Loading [Renamed Thing 2.0.0] (com.example.renamed)",
        online_mod("TotallyDifferentName", "2.5.0", "com.example.renamed"),
    )

    assert "RenamedThing 2.0.0 -> 2.5.0" in result
    assert "https://mods/TotallyDifferentName" in result


def test_falls_back_to_the_name_when_the_guid_is_unknown():
    # Nexus mods are never decompiled, so they carry no guid to match against
    result = compare(
        "[Info   :   BepInEx] Loading [Some Old Mod 1.0.0] (com.example.unlisted)",
        online_mod("SomeOldMod", "1.1.0", source=NEXUS),
    )

    assert "SomeOldMod 1.0.0 -> 1.1.0" in result


def test_matches_by_name_when_the_log_has_no_guid():
    result = compare(
        "[Info   :   BepInEx] Loading [Some Old Mod 1.0.0]",
        online_mod("SomeOldMod", "1.1.0", "com.example.someoldmod"),
    )

    assert "SomeOldMod 1.0.0 -> 1.1.0" in result


def test_guid_finds_the_mod_that_lost_the_name_collision():
    # both are called "Evasion" online, only one of them can hold the name slot
    result = compare(
        "[Info   :   BepInEx] Loading [Evasion 1.0.0] (com.computer.evasion)",
        online_mod("Evasion", "9.9.9", "some.other.author.evasion"),
        online_mod("Evasion", "1.2.0", "com.computer.evasion", source=HEXIUM),
    )

    assert "Evasion 1.0.0 -> 1.2.0" in result
    assert "9.9.9" not in result


def test_unknown_mods_are_left_out():
    result = compare("[Info   :   BepInEx] Loading [Unknown Mod 1.0.0] (com.example.unknown)")

    assert result == ""


def test_name_collisions_keep_both_mods_in_the_guid_index():
    by_name, by_guid = indexed(
        online_mod("Evasion", "9.9.9", "some.other.author.evasion"),
        online_mod("Evasion", "1.2.0", "com.computer.evasion", source=HEXIUM),
    )

    assert len(by_name) == 1
    assert set(by_guid) == {"some.other.author.evasion", "com.computer.evasion"}
    assert str(by_guid["com.computer.evasion"].version) == "1.2.0"
    assert str(by_guid["some.other.author.evasion"].version) == "9.9.9"


def test_guid_index_skips_sources_without_a_guid():
    by_name, by_guid = indexed(online_mod("SomeOldMod", "1.1.0", source=NEXUS))

    assert set(by_name) == {"someoldmod"}
    assert by_guid == {}


def test_guid_index_merges_the_urls_of_every_host_offering_the_mod():
    by_name, by_guid = indexed(
        online_mod("AzuAutoStore", "3.2.0", "Azumatt.AzuAutoStore"),
        online_mod("AzuAutoStoreMirror", "3.2.0", "Azumatt.AzuAutoStore", source=HEXIUM),
    )

    assert by_guid["Azumatt.AzuAutoStore"].urls == ["https://mods/AzuAutoStore", "https://mods/AzuAutoStoreMirror"]
    # the two names never collide, so each keeps only its own url in the name index
    assert by_name["azuautostore"].urls == ["https://mods/AzuAutoStore"]


def test_the_two_indexes_do_not_share_url_lists():
    # the Nexus reupload joins the name group but not the guid group
    by_name, by_guid = indexed(
        online_mod("AzuAutoStore", "3.2.0", "Azumatt.AzuAutoStore", url="https://thunderstore/azu"),
        online_mod("AzuAutoStore", "3.2.0", source=NEXUS, url="https://nexus/azu"),
    )

    assert by_name["azuautostore"].urls == ["https://thunderstore/azu", "https://nexus/azu"]
    assert by_guid["Azumatt.AzuAutoStore"].urls == ["https://thunderstore/azu"]
