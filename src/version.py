"""Lenient version parsing for the version strings mod authors actually upload.

``packaging.Version`` is the wrong tool here for two reasons:

* It raises on a meaningful slice of the corpus (``Beta-1.2.1``, ``v.1.0.0``,
  ``1..0``, ``.0.1``, ``Latest``, ``asdasdasda``), so every call site would need
  a try/except and an invented fallback.
* Where it does parse, PEP 440 semantics disagree with mod conventions: it reads
  ``1.0.4a`` as a *pre*-release of ``1.0.4``, while mod authors mean a hotfix
  *after* ``1.0.4``.

:class:`Version` never raises and defines a *total* order, so ``sorted()``,
``max()`` and ``Mod.__lt__`` are always well defined, including between two
pieces of garbage. Ordering is by, in order of significance:

1. parsability -- anything without a number sorts below every real version,
   including ``0``;
2. the release tuple, with trailing zeros insignificant (``1.0 == 1.0.0``);
3. the pre-release marker (``dev`` < ``alpha`` < ``beta`` < ``rc`` < final),
   found anywhere in the string so ``Beta-1.2.1 < 1.2.1``;
4. a trailing single-letter hotfix marker (``1.0.4 < 1.0.4a``);
5. the remaining text, lowercased and stripped of punctuation -- never
   meaningful, only there to keep the order total and deterministic.
"""

import re
from functools import total_ordering
from typing import Optional, Tuple

__all__ = ["Version", "parse"]

# The first run of dot-separated integers anywhere in the string. Lets junk
# prefixes fall away: ``E.g.1.12.1`` -> 1.12.1, ``bepin5.4.19.0`` -> 5.4.19.0.
_RELEASE_RE = re.compile(r"\d+(?:\.\d+)*")
# A spelled-out pre-release word plus an optional number: ``-beta.1``, ``Beta0``.
_PRE_RE = re.compile(
    r"(?<![a-z])(dev|snapshot|nightly|alpha|beta|preview|pre|rc)(?![a-z])[^a-z0-9]*(\d+)?",
    re.IGNORECASE,
)
# A bare letter directly after the release and nothing else: the ``a`` of ``1.0.4a``.
_POST_RE = re.compile(r"^[a-z]$", re.IGNORECASE)
_JUNK_RE = re.compile(r"[^a-z0-9]+")

_PRE_RANKS = {
    "dev": 0,
    "snapshot": 0,
    "nightly": 0,
    "alpha": 1,
    "beta": 2,
    "pre": 3,
    "preview": 3,
    "rc": 3,
}
_FINAL: Tuple[int, int] = (4, 0)


def _normalize(text: str) -> str:
    """Strip a ``v`` prefix and make a leading dot mean a leading zero."""
    text = text.strip()
    had_v = len(text) > 1 and text[0] in "vV" and (text[1].isdigit() or text[1] == ".")
    if had_v:
        text = text[1:]
    if text.startswith("."):
        # ``v.1`` is "version 1"; a bare ``.5`` is "0.5".
        text = text[1:] if had_v else "0" + text
    return text


@total_ordering
class Version:
    """A parsed mod version. Construction never fails.

    ``str(version)`` returns the original string, so user-facing output keeps
    whatever the author wrote. A version with no digits at all is falsy.
    """

    __slots__ = ("raw", "valid", "release", "pre", "post", "tag")

    raw: str
    valid: bool
    release: Tuple[int, ...]
    pre: Tuple[int, int]
    post: int
    tag: str

    def __init__(self, raw: Optional[str]):
        self.raw = raw if isinstance(raw, str) else ""
        text = _normalize(self.raw)

        match = _RELEASE_RE.search(text)
        if match is None:
            self.valid = False
            self.release = ()
            self.pre = _FINAL
            self.post = 0
            self.tag = _JUNK_RE.sub("", text.lower())
            return

        self.valid = True
        release = [int(part) for part in match.group().split(".")]
        while release and release[-1] == 0:
            # Trailing zeros carry no information: 1.0.0 is 1, and 0.0 is 0.
            release.pop()
        self.release = tuple(release)

        prefix, suffix = text[: match.start()], text[match.end() :]
        if _POST_RE.match(suffix):
            self.post = ord(suffix.lower()) - ord("a") + 1
            suffix = ""
        else:
            self.post = 0

        rest = prefix + " " + suffix
        pre_match = _PRE_RE.search(rest)
        if pre_match is None:
            self.pre = _FINAL
        else:
            self.pre = (_PRE_RANKS[pre_match.group(1).lower()], int(pre_match.group(2) or 0))
            rest = rest[: pre_match.start()] + " " + rest[pre_match.end() :]

        self.tag = _JUNK_RE.sub("", rest.lower())

    @property
    def _key(self):
        return (self.valid, self.release, self.pre, self.post, self.tag)

    def __bool__(self) -> bool:
        return self.valid

    def __str__(self) -> str:
        return self.raw

    def __repr__(self) -> str:
        return f"Version({self.raw!r})"

    def __hash__(self) -> int:
        return hash(self._key)

    def __eq__(self, other) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key == other._key

    def __lt__(self, other) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key < other._key


def parse(text: Optional[str]) -> Version:
    return Version(text)
