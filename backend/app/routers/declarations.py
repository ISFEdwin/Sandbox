"""Declaration intake: a broad-brush fit against the published gates.

``POST /api/declarations/intake`` does not store a declaration and does not
decide an environmental permit or a section 16 application. It returns the
fit object and a one-page annex filled from the reference file.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.government_fit import DeclarationIntake, DeclarationIntakeResult
from app.services.government_fit import declaration_intake

router = APIRouter(tags=["declarations"])


@router.post("/declarations/intake", response_model=DeclarationIntakeResult)
def intake(body: DeclarationIntake) -> DeclarationIntakeResult:
    """Fit the declared facts. Missing facts are listed, not guessed."""
    result = declaration_intake(body)
    return DeclarationIntakeResult.model_validate(result)
