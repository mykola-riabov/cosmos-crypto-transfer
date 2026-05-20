"""BIP39 mnemonic generation, validation, and private-key import helpers."""

from __future__ import annotations

import re

from bip_utils import Bip39MnemonicGenerator, Bip39MnemonicValidator, Bip39WordsNum

_HEX_RE = re.compile(r'^(0x)?[0-9a-fA-F]{64}$')


def generate_mnemonic(words: int = 24) -> str:
    if words not in (12, 24):
        raise ValueError('Mnemonic length must be 12 or 24 words.')
    num = Bip39WordsNum.WORDS_NUM_24 if words == 24 else Bip39WordsNum.WORDS_NUM_12
    return str(Bip39MnemonicGenerator().FromWordsNumber(num))


def validate_mnemonic(mnemonic: str) -> None:
    phrase = (mnemonic or '').strip()
    if not phrase:
        raise ValueError('Mnemonic is empty.')
    Bip39MnemonicValidator().Validate(phrase)


def parse_private_key_hex(raw: str) -> bytes:
    """32-byte secp256k1 private key (64 hex chars, optional 0x prefix)."""
    text = (raw or '').strip().replace(' ', '')
    if not _HEX_RE.match(text):
        raise ValueError('Private key must be 64 hex characters (32 bytes).')
    if text.lower().startswith('0x'):
        text = text[2:]
    key = bytes.fromhex(text)
    if len(key) != 32:
        raise ValueError('Private key must be 32 bytes.')
    return key


def looks_like_private_key(raw: str) -> bool:
    try:
        parse_private_key_hex(raw)
        return True
    except ValueError:
        return False


def normalize_secret_input(raw: str) -> tuple[str, str]:
    """
    Classify pasted secret. Returns (kind, value).
    kind: 'mnemonic' | 'private_key'
    """
    text = (raw or '').strip()
    if not text:
        raise ValueError('Enter a mnemonic or private key.')
    if looks_like_private_key(text):
        return 'private_key', text
    validate_mnemonic(text)
    return 'mnemonic', text
