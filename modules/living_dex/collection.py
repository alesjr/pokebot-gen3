from __future__ import annotations

from dataclasses import dataclass, field

from modules.pokemon import Pokemon


PERFECT_IV_SUM = 6 * 31


def is_qualified(pokemon: Pokemon) -> bool:
    """Return whether a Pokémon may count toward the Living Dex."""
    return pokemon.is_shiny or pokemon.ivs.sum() == PERFECT_IV_SUM


def is_founder_candidate(pokemon: Pokemon, minimum_iv_sum: int = 93) -> bool:
    """Founder must be common, usable, and at least average by aggregate IVs."""
    return not pokemon.is_egg and not is_qualified(pokemon) and pokemon.ivs.sum() >= minimum_iv_sum


def variant_key(pokemon: Pokemon) -> str:
    if pokemon.species.name == "Unown":
        return pokemon.unown_letter
    if pokemon.gender in ("male", "female"):
        return pokemon.gender
    return "any"


@dataclass(frozen=True)
class CollectedPokemon:
    species: str
    national_dex_number: int
    variant: str
    shiny: bool
    perfect_ivs: bool
    box: int
    slot: int


@dataclass
class CollectionSnapshot:
    collected: list[CollectedPokemon] = field(default_factory=list)
    pokemon_count: int = 0
    capacity: int = 14 * 30

    @classmethod
    def from_storage(cls, storage) -> "CollectionSnapshot":
        result = cls(pokemon_count=storage.pokemon_count)
        for box in storage.boxes:
            for slot in box.slots:
                pokemon = slot.pokemon
                if not is_qualified(pokemon):
                    continue
                result.collected.append(
                    CollectedPokemon(
                        species=pokemon.species.name,
                        national_dex_number=pokemon.species.national_dex_number,
                        variant=variant_key(pokemon),
                        shiny=pokemon.is_shiny,
                        perfect_ivs=pokemon.ivs.sum() == PERFECT_IV_SUM,
                        box=box.number + 1,
                        slot=slot.slot_index + 1,
                    )
                )
        return result

    @property
    def free_slots(self) -> int:
        return self.capacity - self.pokemon_count

    def keys(self) -> set[tuple[str, str]]:
        return {(entry.species, entry.variant) for entry in self.collected}
