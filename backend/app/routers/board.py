"""The comparison board route: two schemes, five axes, on the map's data.

HTTP only; every rule lives in ``app/services/board.py``. A new router per the
repo's "new feature, new files" rule. The board is the product's headline
(STATUS.md edge 1), so it sits beside the scenario routes rather than inside
the run that writes overlays.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import Field

from app.config import DEFAULT_RAINFALL_MM
from app.schemas.scene import WireModel

router = APIRouter(tags=["board"])


class BoardRequest(WireModel):
    """``POST /api/scenes/{sceneId}/scenario/board`` body.

    Each scheme is a list of plan ids composed exactly as a run composes them;
    an empty list is today's land cover. The tide is a shared forcing applied
    to both schemes' routed flood extent.
    """

    scheme_a: list[str] = Field(default_factory=list)
    scheme_b: list[str] = Field(default_factory=list)
    rainfall_mm: float = Field(default=DEFAULT_RAINFALL_MM, ge=0, le=800)
    tide_state: str = "low"


@router.post("/scenes/{scene_id}/scenario/board")
def scenario_board(scene_id: str, body: BoardRequest) -> dict:
    """Two schemes side by side on drainage, heat, tide, greenery, wind.

    No combined score and no pass/fail -- each axis keeps its own units and
    the delta between the two readings is the finding. The wind channel is
    the least-cost corridor geometry under the cited prevailing inflow, never
    a velocity ratio. Writes nothing and starts no run.
    """
    from app.services import board as board_service

    try:
        return board_service.board(
            scene_id,
            scheme_a=body.scheme_a,
            scheme_b=body.scheme_b,
            rainfall_mm=body.rainfall_mm,
            tide_state=body.tide_state,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc