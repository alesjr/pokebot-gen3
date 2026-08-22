from __future__ import annotations


def persistent_form(pokemon, rom) -> str:
    if pokemon.species.name == "Unown":
        return pokemon.unown_letter
    if pokemon.species.name == "Deoxys":
        if rom.is_emerald:
            return "speed"
        if rom.is_frlg:
            return "attack" if rom.game_code == "BPR" else "defense"
        return "normal"
    return "any"


def specimen_payload(pokemon, profile: str, rom) -> dict:
    trainer = pokemon.original_trainer
    return {
        "personality_value": pokemon.personality_value,
        "species": pokemon.species.name,
        "national_dex_number": pokemon.species.national_dex_number,
        "ot_name": trainer.name,
        "trainer_id": trainer.id,
        "secret_id": trainer.secret_id,
        "profile": profile,
        "gender": pokemon.gender or "any",
        "form": persistent_form(pokemon, rom),
        "shiny": pokemon.is_shiny,
        "official_event": False,
    }


def profile_specimens(party, storage, profile: str, rom) -> list[dict]:
    pokemon = [member for member in party if not member.is_egg]
    pokemon.extend(
        slot.pokemon
        for box in storage.boxes
        for slot in box.slots
        if not slot.pokemon.is_egg
    )
    return [specimen_payload(member, profile, rom) for member in pokemon]
