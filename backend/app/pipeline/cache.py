"""Content-addressed cache for provider downloads.

Two areas that overlap must not download the same WorldCover tile twice, and a
re-prepare six months later must be able to reuse a pinned snapshot. Both needs
are the same mechanism: store bytes under a key derived from what the bytes are,
not from which area asked for them.

Paths are built from validated segments. A provider name is not user input, but
it arrives from stage code and a traversal bug here would let a stage write
outside the data directory -- the one class of mistake this module is written to
make impossible.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from app.config import settings

_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SAFE_SUFFIX = re.compile(r"^\.[A-Za-z0-9]+$")


class CacheError(ValueError):
    """A cache path or key that would escape the cache root."""


def _segment(value: str, label: str) -> str:
    if not isinstance(value, str) or not _SAFE_SEGMENT.match(value):
        raise CacheError(
            f"{label} {value!r} is not a safe path segment "
            "(letters, digits, '.', '_' and '-' only, not starting with '.')"
        )
    return value


def cache_root() -> Path:
    """``data/cache/sources``. Shared by every area bundle."""
    return settings.data_dir / "cache" / "sources"


def content_key(*parts: str, length: int = 16) -> str:
    """A stable short key for a source artefact.

    Same inputs give the same key on every machine, which is what makes a pinned
    ``sources.lock.json`` reproducible. The separator cannot appear in a URL, a
    tile id or a feature number, so a shift of one part into the next cannot
    collide.
    """
    if not parts:
        raise CacheError("content_key needs at least one part")
    digest = hashlib.sha256("\x1f".join(str(p) for p in parts).encode("utf-8"))
    return digest.hexdigest()[:length]


def source_path(provider: str, dataset: str, key: str, suffix: str) -> Path:
    """Where one provider artefact lives. Does not create the file."""
    provider = _segment(provider, "provider")
    dataset = _segment(dataset, "dataset")
    key = _segment(key, "key")
    if not _SAFE_SUFFIX.match(suffix):
        raise CacheError(
            f"suffix {suffix!r} must be a dot followed by letters or digits, "
            "e.g. '.tif' or '.geojson'"
        )
    return cache_root() / provider / dataset / f"{key}{suffix}"


def write_atomic(path: Path, data: bytes) -> Path:
    """Write bytes so a reader never sees a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    return path


def read_bytes(path: Path) -> bytes | None:
    """The cached bytes, or None when the artefact is absent."""
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def is_pinned(area_dir: Path) -> bool:
    """True when the area's source snapshot has been locked."""
    return (area_dir / "sources.lock.json").exists()
