import unittest

from project_utils.wallet_mnemonic import (
    generate_mnemonic,
    looks_like_private_key,
    normalize_secret_input,
    validate_mnemonic,
)


class TestWalletMnemonic(unittest.TestCase):
    def test_generate_and_validate_24(self):
        phrase = generate_mnemonic(24)
        self.assertEqual(len(phrase.split()), 24)
        validate_mnemonic(phrase)

    def test_generate_12(self):
        phrase = generate_mnemonic(12)
        self.assertEqual(len(phrase.split()), 12)

    def test_private_key_detect(self):
        hex_key = 'ab' * 32
        self.assertTrue(looks_like_private_key(hex_key))
        kind, _ = normalize_secret_input(hex_key)
        self.assertEqual(kind, 'private_key')


if __name__ == '__main__':
    unittest.main()
