"""Token encryption at rest."""

import pytest

from app.core.crypto import TokenCipher, TokenDecryptError, generate_key


def test_tokens_round_trip_and_are_not_stored_in_plain_text() -> None:
    cipher = TokenCipher(generate_key())

    stored = cipher.encrypt("spotify-refresh-token")

    assert "spotify-refresh-token" not in stored
    assert cipher.decrypt(stored) == "spotify-refresh-token"


def test_same_token_encrypts_differently_each_time() -> None:
    cipher = TokenCipher(generate_key())

    assert cipher.encrypt("same") != cipher.encrypt("same")


def test_wrong_key_or_tampering_is_detected() -> None:
    stored = TokenCipher(generate_key()).encrypt("secret")

    with pytest.raises(TokenDecryptError):
        TokenCipher(generate_key()).decrypt(stored)
    with pytest.raises(TokenDecryptError):
        TokenCipher(generate_key()).decrypt(stored[:-4] + "AAAA")
