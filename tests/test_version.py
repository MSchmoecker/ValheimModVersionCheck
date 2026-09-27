import datetime
import json
import random
from pathlib import Path

import pytest

from src import Mod
from src.mod import THUNDERSTORE, HEXIUM, NEXUS
from src.version import Version

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def corpus():
    """Every version string that appears in the shipped mod data."""
    found = set()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("version", "online_version") and isinstance(value, str):
                    found.add(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for path in DATA_DIR.glob("*.json"):
        walk(json.loads(path.read_text()))
    return sorted(found)


@pytest.mark.parametrize("raw, release, pre, post, valid", [
    # plain releases, any number of segments
    ("1.2.3", (1, 2, 3), (4, 0), 0, True),
    ("2020.3.33.23162", (2020, 3, 33, 23162), (4, 0), 0, True),
    ("20251116", (20251116,), (4, 0), 0, True),
    # trailing zeros are insignificant
    ("1.0.0", (1,), (4, 0), 0, True),
    ("0.0", (), (4, 0), 0, True),
    # v prefixes, with or without a dot
    ("V1.5.55", (1, 5, 55), (4, 0), 0, True),
    ("v.1.0.0", (1,), (4, 0), 0, True),
    # a leading dot means a leading zero
    (".5", (0, 5), (4, 0), 0, True),
    (".0.1", (0, 0, 1), (4, 0), 0, True),
    # junk around the numbers is discarded
    ("E.g.1.12.1", (1, 12, 1), (4, 0), 0, True),
    ("bepin5.4.19.0", (5, 4, 19), (4, 0), 0, True),
    ("1.2.", (1, 2), (4, 0), 0, True),
    ("1..0", (1,), (4, 0), 0, True),
    ("0.8.1-IngotStacks", (0, 8, 1), (4, 0), 0, True),
    # pre-release markers, wherever they sit
    ("0.1.15-alpha", (0, 1, 15), (1, 0), 0, True),
    ("0.4.3-beta.1", (0, 4, 3), (2, 1), 0, True),
    ("1.0.1.beta", (1, 0, 1), (2, 0), 0, True),
    ("Beta-1.2.1", (1, 2, 1), (2, 0), 0, True),
    ("0.1.15-rune-preview", (0, 1, 15), (3, 0), 0, True),
    # a lone trailing letter is a hotfix, not a pre-release
    ("1.0.4a", (1, 0, 4), (4, 0), 1, True),
    ("0.5b", (0, 5), (4, 0), 2, True),
    # no digits at all
    ("Latest", (), (4, 0), 0, False),
    ("asdasdasda", (), (4, 0), 0, False),
    ("", (), (4, 0), 0, False),
])
def test_parses_real_world_shapes(raw, release, pre, post, valid):
    parsed = Version(raw)
    assert (parsed.release, parsed.pre, parsed.post, parsed.valid) == (release, pre, post, valid)


def test_str_keeps_the_original_text():
    assert str(Version("v.1.0.0")) == "v.1.0.0"
    assert str(Version("Latest")) == "Latest"


def test_numeric_segments_compare_numerically_not_lexically():
    assert Version("1.2.9") < Version("1.2.10")
    assert Version("0.9.9") < Version("0.10.0")


def test_trailing_zeros_and_v_prefixes_are_equal():
    assert Version("1") == Version("1.0") == Version("1.0.0.0") == Version("v1.0")
    assert Version("1.0") < Version("1.0.0.1")


def test_pre_release_sorts_below_its_release():
    assert Version("1.2.1-dev") < Version("1.2.1-alpha") < Version("1.2.1-beta")
    assert Version("1.2.1-beta") < Version("1.2.1-rc") < Version("1.2.1")
    assert Version("1.2.1-beta") < Version("1.2.1-beta.1")
    assert Version("Beta-1.2.1") < Version("1.2.1")


def test_hotfix_letter_sorts_above_its_release():
    assert Version("1.0.4") < Version("1.0.4a") < Version("1.0.4b")
    assert Version("1.0.4a") < Version("1.0.5")


def test_unparsable_versions_sort_below_every_real_version():
    assert Version("Latest") < Version("0")
    assert Version("yes") < Version("0.0.0")
    assert not Version("Latest")
    assert Version("0")


def test_unparsable_versions_still_have_a_deterministic_order():
    assert Version("a") < Version("b")
    assert Version("Latest") == Version("latest")
    assert Version("Latest") != Version("Newest")


def test_an_unknown_suffix_does_not_outrank_the_release():
    assert Version("0.8.1") < Version("0.8.1-IngotStacks") < Version("0.8.2")


@pytest.mark.parametrize("raw", [None, 42, "", "   ", "-", "...", "\x00"])
def test_construction_never_raises(raw):
    assert isinstance(Version(raw), Version)


def test_every_shipped_version_parses_without_raising():
    versions = corpus()
    assert len(versions) > 1000, "corpus did not load"
    for raw in versions:
        Version(raw)


def test_ordering_over_the_whole_corpus_is_total_and_stable():
    versions = [Version(raw) for raw in corpus()]

    # The sorted sequence is determined up to equality: "0" and "0.0.0" are the
    # same version, so only their shared rank is fixed, not which text lands first.
    shuffled = versions[:]
    random.Random(0).shuffle(shuffled)
    assert sorted(versions) == sorted(shuffled)

    ordered = sorted(versions)
    for low, high in zip(ordered, ordered[1:]):
        assert low <= high
        assert not high < low


def test_comparison_with_a_foreign_type_is_rejected():
    with pytest.raises(TypeError):
        Version("1.0") < "1.0"
    assert Version("1.0") != "1.0"


def mod(version, source=THUNDERSTORE, is_modpack=False, updated=datetime.datetime(2024, 1, 1)):
    return Mod("Some Mod", version, updated, False, is_modpack, source, "", "url", [])


@pytest.mark.parametrize("decompilable", [THUNDERSTORE, HEXIUM])
def test_mod_lt_prefers_decompilable_sources_over_nexus(decompilable):
    # Mod.__lt__ means "is the better candidate"; update_mod_list takes sorted(...)[0].
    assert mod("0.0.1", source=decompilable) < mod("9.9.9", source=NEXUS)


def test_mod_lt_ranks_thunderstore_and_hexium_equally():
    # Neither outranks the other, so a full tie is decided by the order update_mod_list
    # appends the sources in, which the stable sort preserves.
    assert not mod("1.0", source=THUNDERSTORE) < mod("1.0", source=HEXIUM)
    assert not mod("1.0", source=HEXIUM) < mod("1.0", source=THUNDERSTORE)
    assert sorted([mod("1.0", source=THUNDERSTORE), mod("1.0", source=HEXIUM)])[0].source == THUNDERSTORE
    assert sorted([mod("1.0", source=HEXIUM), mod("1.0", source=THUNDERSTORE)])[0].source == HEXIUM


def test_mod_lt_prefers_the_higher_version_across_equally_ranked_sources():
    assert mod("2.0", source=HEXIUM) < mod("1.0", source=THUNDERSTORE)
    assert mod("2.0", source=THUNDERSTORE) < mod("1.0", source=HEXIUM)


def test_mod_lt_prefers_non_modpacks():
    assert mod("0.0.1") < mod("9.9.9", is_modpack=True)


def test_mod_lt_prefers_the_higher_version():
    assert mod("1.2.10") < mod("1.2.9")
    assert not mod("1.2.9") < mod("1.2.10")


def test_mod_lt_falls_back_to_the_older_upload():
    older = mod("1.0", updated=datetime.datetime(2023, 1, 1))
    newer = mod("1.0.0", updated=datetime.datetime(2024, 1, 1))
    assert older < newer
    assert not newer < older


def test_mod_lt_ranks_garbage_versions_last():
    assert mod("0.0.1") < mod("Latest")
    best = sorted([mod("Latest"), mod("1.0"), mod("2.0")])[0]
    assert str(best.version) == "2.0"
