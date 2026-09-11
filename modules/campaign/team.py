from __future__ import annotations

from itertools import combinations
from typing import Iterable

from modules.pokemon import Pokemon


def pokemon_identity(pokemon: Pokemon) -> tuple[int, int, int, int]:
    trainer = pokemon.original_trainer
    return (
        pokemon.personality_value,
        pokemon.species.index,
        trainer.id,
        trainer.secret_id,
    )


def combat_potential(pokemon: Pokemon) -> int:
    return pokemon.species.base_stats.sum() + pokemon.ivs.sum()


def _combat_rank(pokemon: Pokemon) -> tuple[int, int, tuple[int, int, int, int]]:
    return (-combat_potential(pokemon), -pokemon.ivs.sum(), pokemon_identity(pokemon))


def hm_coverage(pokemon: Pokemon, required_hms: Iterable[str]) -> frozenset[str]:
    required = {name.casefold(): name for name in required_hms}
    coverage: set[str] = set()
    for entry in pokemon.species.learnset.tm_hm:
        for known_name in (entry.item.name, entry.move.name):
            if known_name.casefold() in required:
                coverage.add(required[known_name.casefold()])
    return frozenset(coverage)


def _deduplicate(pokemon: Iterable[Pokemon]) -> list[Pokemon]:
    unique: dict[tuple[int, int, int, int], Pokemon] = {}
    for candidate in pokemon:
        unique.setdefault(pokemon_identity(candidate), candidate)
    return list(unique.values())


def _best_hm_group(
    candidates: list[Pokemon],
    required_hms: tuple[str, ...],
    included: list[Pokemon],
    target_size: int,
) -> tuple[list[Pokemon], int]:
    if not required_hms:
        return [], 0

    included_ids = {pokemon_identity(pokemon) for pokemon in included}
    by_coverage: dict[frozenset[str], Pokemon] = {}
    options: list[Pokemon] = []
    for candidate in candidates:
        coverage = hm_coverage(candidate, required_hms)
        if not coverage:
            continue
        if pokemon_identity(candidate) in included_ids:
            options.append(candidate)
        elif coverage not in by_coverage or _combat_rank(candidate) < _combat_rank(by_coverage[coverage]):
            by_coverage[coverage] = candidate
    options.extend(by_coverage.values())
    options = _deduplicate(options)

    best_group: list[Pokemon] = []
    best_coverage = 0
    best_rank: tuple | None = None
    max_group_size = min(len(required_hms), len(options), target_size)
    for group_size in range(1, max_group_size + 1):
        for group in combinations(options, group_size):
            combined_ids = included_ids | {pokemon_identity(pokemon) for pokemon in group}
            if len(combined_ids) > target_size:
                continue
            coverages = [hm_coverage(pokemon, required_hms) for pokemon in group]
            covered = set().union(*coverages)
            rank = (
                -len(covered),
                group_size,
                tuple(sorted((-len(coverage) for coverage in coverages))),
                tuple(sorted(_combat_rank(pokemon) for pokemon in group)),
                tuple(sorted(pokemon_identity(pokemon) for pokemon in group)),
            )
            if best_rank is None or rank < best_rank:
                best_rank = rank
                best_group = list(group)
                best_coverage = len(covered)
    return best_group, best_coverage


def _required_species(
    candidates: list[Pokemon], temporary_required_species: Iterable[str]
) -> list[Pokemon]:
    selected: list[Pokemon] = []
    for species_name in dict.fromkeys(name.casefold() for name in temporary_required_species):
        matches = [
            pokemon for pokemon in candidates if pokemon.species.name.casefold() == species_name
        ]
        if matches:
            selected.append(min(matches, key=_combat_rank))
    return _deduplicate(selected)


def select_campaign_party(
    party: Iterable[Pokemon],
    stored: Iterable[Pokemon],
    *,
    target_size: int,
    required_hms: Iterable[str] = (),
    temporary_required_species: Iterable[str] = (),
) -> list[Pokemon]:
    party = list(party)
    stored = list(stored)
    candidates = _deduplicate(
        pokemon
        for pokemon in (*party, *stored)
        if not pokemon.is_shiny and not pokemon.is_egg
    )
    target_size = min(max(target_size, 1), 6, len(candidates))
    if target_size == 0:
        return []

    required = _required_species(candidates, temporary_required_species)[:target_size]
    hm_names = tuple(dict.fromkeys(required_hms))
    candidate_ids = {pokemon_identity(candidate) for candidate in candidates}
    current = [
        pokemon for pokemon in party if pokemon_identity(pokemon) in candidate_ids
    ]
    current_hm, current_coverage = _best_hm_group(
        current, hm_names, required, target_size
    )
    best_hm, best_coverage = _best_hm_group(
        candidates, hm_names, required, target_size
    )

    current_fits = len({pokemon_identity(pokemon) for pokemon in (*required, *current_hm)}) <= target_size
    if (
        current_fits
        and current_hm
        and best_coverage <= current_coverage
        and len(best_hm) >= len(current_hm)
    ):
        hm_group = current_hm
    else:
        hm_group = best_hm

    selected = _deduplicate((*required, *hm_group))
    selected_ids = {pokemon_identity(pokemon) for pokemon in selected}
    for candidate in sorted(candidates, key=_combat_rank):
        if len(selected) >= target_size:
            break
        if pokemon_identity(candidate) not in selected_ids:
            selected.append(candidate)
            selected_ids.add(pokemon_identity(candidate))
    return selected
