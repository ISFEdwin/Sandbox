"""Wire shape of a government-criteria fit read.

The read is broad-brush. ``notADetermination`` is true on every response, the
screening label is fixed, and ``furtherInformation`` is the unknowns list. A
response that drops either the label or that list does not validate.

Field names follow the intake object: ``schedule3``, ``schedule2``,
``planningPermission``, ``eaMayBeRequired``, ``assumptions``,
``furtherInformation``, ``notADetermination``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.scene import WireModel

#: On every fit read and on the screening-basis annex. E2 and the Code of
#: Practice treat a missing label as a failed output, not as a shorter one.
SCREENING_LABEL = "BROAD_BRUSH_FIT_READ_NOT_A_STATUTORY_DETERMINATION"


class ThresholdSnapshot(WireModel):
    """One reference-file entry, copied onto the read that used it."""

    id: str
    value: float | str | None = None
    unit: str
    comparator: str | None = None
    source_url: str
    effective_date: str | None = None
    superseded_by: str | None = None


class Schedule3Read(WireModel):
    """Schedule 3 item 1, applied to an area in hectares."""

    triggered: bool
    flag: Literal["review", "not_triggered", "insufficient_facts"]
    site_area_ha: float | None = None
    threshold: ThresholdSnapshot
    reason: str


class Schedule2Flag(WireModel):
    """A Schedule 2 item the declared facts meet. Absent means not flagged."""

    item: str
    triggered: Literal[True]
    reason: str
    threshold: ThresholdSnapshot


class PlanningPermissionRead(WireModel):
    """Column 1 / Column 2 / neither. A planning permission is not an environmental permit."""

    column: Literal["1", "2", "neither"] | None = None
    route: Literal["column1", "s16", "s12A"] | None = None
    is_environmental_permit: Literal[False]
    permission_predates_eiao: bool
    note: str


class Section44Read(WireModel):
    """Section 4(4). A flag for a possible specification. Aggregation is not asserted."""

    flag: Literal["possible_specification", "not_indicated", "insufficient_facts"]
    asserted_aggregation: Literal[False]
    note: str


class HkpsgAdvisory(WireModel):
    """Table 1.3 and NEF 25, as a check against HKPSG. Never a pass or a fail."""

    advisory_only: Literal[True]
    pass_fail: Literal[False]
    applied_open_space_separation_as_residential: Literal[False]
    residential_buffer_m: float | None = None
    note: str


class GovernmentFit(WireModel):
    """The fit object returned at declaration intake."""

    screening_label: str
    not_a_determination: Literal[True]
    schedule3: Schedule3Read
    schedule2: list[Schedule2Flag] = Field(default_factory=list)
    planning_permission: PlanningPermissionRead
    ea_may_be_required: bool | None = None
    assumptions: list[str]
    further_information: list[str]
    section44: Section44Read
    hkpsg: HkpsgAdvisory
    as_at: dict[str, str]

    @field_validator("screening_label")
    @classmethod
    def _label(cls, value: str) -> str:
        if value != SCREENING_LABEL:
            raise ValueError("screening label missing")
        return value

    @field_validator("assumptions", "further_information")
    @classmethod
    def _register(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("the unknowns list is part of the fit read")
        return value


class DeclarationIntake(WireModel):
    """Facts a declaration may hold. An absent fact is not filled in."""

    site_area_ha: float | None = None
    coverage_fraction: float | None = None
    district_area_ha: float | None = None
    population: int | None = None
    flat_count: int | None = None
    served_by_public_sewerage: bool | None = None
    ozp_column: Literal["1", "2", "neither"] | None = None
    road_class: str | None = None
    road_length_m: float | None = None
    road_screening: bool | None = None
    reclamation_ha: float | None = None
    reclamation_specified_area_seaward_m: float | None = None
    reclamation_specified_area_landward_m: float | None = None
    reclamation_residential_m: float | None = None
    dredging_m3: float | None = None
    dredging_specified_area_seaward_m: float | None = None
    dredging_specified_area_landward_m: float | None = None
    dredging_residential_m: float | None = None
    stp_m3_per_day: float | None = None
    stp_receiver_m: float | None = None
    channel_width_m: float | None = None
    channel_named_area_m: float | None = None
    deep_bay_buffer_zone: Literal["1", "2", "neither"] | None = None
    use: str | None = None
    nteh: bool | None = None
    in_sensitive_area: bool | None = None
    rock_cavern: bool | None = None
    rock_cavern_portal_m: float | None = None
    contiguous_same_or_associated_persons: bool | None = None
    may_cause_impacts: bool | None = None
    pollution_sensitive: bool | None = None
    major_or_large_scale: bool | None = None
    receiver_distance_road_m: float | None = None
    receiver_distance_rail_m: float | None = None
    rail_type: Literal["mtr", "kcr", "lrt"] | None = None
    within_nef_25: bool | None = None
    planning_permission_date: str | None = None

    @model_validator(mode="after")
    def _measures(self) -> "DeclarationIntake":
        numbers = (
            self.site_area_ha,
            self.district_area_ha,
            self.road_length_m,
            self.reclamation_ha,
            self.reclamation_specified_area_seaward_m,
            self.reclamation_specified_area_landward_m,
            self.reclamation_residential_m,
            self.dredging_m3,
            self.dredging_specified_area_seaward_m,
            self.dredging_specified_area_landward_m,
            self.dredging_residential_m,
            self.stp_m3_per_day,
            self.stp_receiver_m,
            self.channel_width_m,
            self.channel_named_area_m,
            self.rock_cavern_portal_m,
            self.receiver_distance_road_m,
            self.receiver_distance_rail_m,
            self.population,
            self.flat_count,
        )
        if any(value is not None and value < 0 for value in numbers):
            raise ValueError("a declared measure cannot be negative")
        if self.coverage_fraction is not None and not 0 <= self.coverage_fraction <= 1:
            raise ValueError("coverage fraction is a share of the district, from 0 to 1")
        return self


class DeclarationIntakeResult(WireModel):
    """Intake response: the fit object and the pasteable screening-basis annex."""

    government_fit: GovernmentFit
    screening_basis_annex: str
