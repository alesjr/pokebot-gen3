from __future__ import annotations

from dataclasses import dataclass

from modules.pokemon import get_species_by_national_dex


UNOWN_FORMS = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ("!", "?")
DEOXYS_FORMS = ("normal", "attack", "defense", "speed")


@dataclass(frozen=True, order=True)
class CollectionTarget:
    national_dex_number: int
    species: str
    variant: str
    shiny_required: bool
    official_event_required: bool = False


def _gender_variants(gender_ratio: int) -> tuple[str, ...]:
    if gender_ratio == 255:
        return ("any",)
    if gender_ratio == 0:
        return ("male",)
    if gender_ratio == 254:
        return ("female",)
    return ("male", "female")


def build_collection_targets() -> tuple[CollectionTarget, ...]:
    targets: list[CollectionTarget] = []
    for number in range(1, 387):
        species = get_species_by_national_dex(number)
        if species.name == "Unown":
            variants = UNOWN_FORMS
        elif species.name == "Deoxys":
            variants = DEOXYS_FORMS
        elif species.name == "Spinda":
            variants = ("any",)
        else:
            variants = _gender_variants(species.gender_ratio)
        for variant in variants:
            targets.append(
                CollectionTarget(
                    national_dex_number=number,
                    species=species.name,
                    variant=variant,
                    shiny_required=species.name != "Celebi",
                    official_event_required=species.name == "Celebi",
                )
            )
    return tuple(targets)


def validate_collection_targets(targets: tuple[CollectionTarget, ...]) -> None:
    shiny_species = {target.national_dex_number for target in targets if target.shiny_required}
    if len(shiny_species) != 385:
        raise ValueError(f"expected 385 shiny species, got {len(shiny_species)}")
    celebi = [target for target in targets if target.species == "Celebi"]
    if len(celebi) != 1 or celebi[0].shiny_required or not celebi[0].official_event_required:
        raise ValueError("Celebi must be one normal official-event target")
    unown = [target for target in targets if target.species == "Unown"]
    if {target.variant for target in unown} != set(UNOWN_FORMS):
        raise ValueError("Unown must contain exactly 28 forms")
    spinda = [target for target in targets if target.species == "Spinda"]
    if len(spinda) != 1 or spinda[0].variant != "any":
        raise ValueError("Spinda patterns must not create infinite targets")
    if len(targets) != len(set(targets)):
        raise ValueError("collection targets must be unique")
