"""Encrypting Spotify tokens before they are stored (threat T7).

Fernet (from the ``cryptography`` package) is authenticated encryption: a stored value
can't be read *or* changed without the key. The key lives only in the environment
(TOKEN_ENCRYPTION_KEY), never in the database, so a database leak alone does not
expose anyone's Spotify account. Atlas also encrypts its disks; this is a second layer.
"""

from cryptography.fernet import Fernet, InvalidToken


class TokenDecryptError(Exception):
    """A stored token could not be decrypted (wrong key, or the value was tampered with)."""


class TokenCipher:
    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as error:
            raise TokenDecryptError("stored token could not be decrypted") from error


def generate_key() -> str:
    """A new random key for TOKEN_ENCRYPTION_KEY (see README: "Spotify login")."""
    return Fernet.generate_key().decode()
