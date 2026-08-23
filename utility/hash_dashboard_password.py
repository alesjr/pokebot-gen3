"""Print an Argon2id hash suitable for POKEBOT_WEB_PASSWORD_HASH."""

from getpass import getpass

from argon2 import PasswordHasher


if __name__ == "__main__":
    password = getpass("Senha do dashboard: ")
    confirmation = getpass("Repita a senha: ")
    if password != confirmation:
        raise SystemExit("Senhas diferentes.")
    if len(password) < 12:
        raise SystemExit("Use pelo menos 12 caracteres.")
    print(PasswordHasher().hash(password))
