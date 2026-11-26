"""Provider adapters: one shape for every external source.

A stage should not know whether its input arrived from a FeatureServer, an
Overpass query, a STAC item or a file already on disk. It asks a source for a
:class:`Fetched`, and the fetching, retrying, paging and provenance recording
happen behind that interface.

Two rules for every adapter:

* **Provenance is part of the return value.** A download without a retrieval
  date, dataset id and licence cannot be cited, and an uncitable input is not
  usable in a bundle that publishes numbers.
* **A partial fetch is a failure, not a short list.** The CSDI FeatureServer
  caps every response (``exceededTransferLimit``); an adapter that stops at the
  first page returns a plausible, under-counted layer. Page on ``resultOffset``
  and check the total against ``returnCountOnly``.

No adapters are implemented yet. Increment B adds ``dsd.py``; Increment C adds
the rest.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from app.pipeline.manifest import Gate, SourceRef


class SourceError(RuntimeError):
    """A provider could not be read, with the provider and reason named."""


@dataclass
class Fetched:
    """What an adapter returns: local files, provenance, and any gate it moved."""

    files: list[Path] = field(default_factory=list)
    sources: list[SourceRef] = field(default_factory=list)
    gates: list[Gate] = field(default_factory=list)
    #: Non-fatal limits the caller must carry into the seal. e.g. "layer
    #: returned 0 engineered channels in this extent".
    notes: list[str] = field(default_factory=list)

    def merge(self, other: Fetched) -> Fetched:
        return Fetched(
            files=[*self.files, *other.files],
            sources=[*self.sources, *other.sources],
            gates=[*self.gates, *other.gates],
            notes=[*self.notes, *other.notes],
        )


class Source(Protocol):
    """The one method an adapter implements."""

    provider: str
    dataset: str

    def fetch(self, bounds: tuple[float, float, float, float],
              dest: Path, *, offline: bool = False) -> Fetched:
        ...
