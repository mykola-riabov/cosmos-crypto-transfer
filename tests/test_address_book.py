import unittest

from project_utils.address_book import resolve_wallets

SAMPLE = [
    {'name': 'wallet_1_osmosis', 'network': 'osmosis', 'address': 'osmo1aaa'},
    {'name': 'wallet_1_juno', 'network': 'juno', 'address': 'juno1bbb'},
]

SAMPLE_SHORT_NAMES = [
    {'name': 'w1_osmosis', 'network': 'osmosis', 'address': 'osmo1aaa'},
    {'name': 'w1_juno', 'network': 'juno', 'address': 'juno1bbb'},
]


class TestAddressBook(unittest.TestCase):
    def test_resolve_both_wallets(self):
        s_name, s_addr, r_name, r_addr = resolve_wallets(
            SAMPLE, 'wallet_1_osmosis', 'wallet_1_juno'
        )
        self.assertEqual(s_name, 'wallet_1_osmosis')
        self.assertEqual(s_addr, 'osmo1aaa')
        self.assertEqual(r_name, 'wallet_1_juno')
        self.assertEqual(r_addr, 'juno1bbb')

    def test_resolve_legacy_keys_against_short_book_names(self):
        """IBC routes still use wallet_1_* while the address book uses w1_*."""
        s_name, s_addr, r_name, r_addr = resolve_wallets(
            SAMPLE_SHORT_NAMES, 'wallet_1_osmosis', 'wallet_1_juno'
        )
        self.assertEqual(s_name, 'w1_osmosis')
        self.assertEqual(s_addr, 'osmo1aaa')
        self.assertEqual(r_name, 'w1_juno')
        self.assertEqual(r_addr, 'juno1bbb')

    def test_resolve_short_keys_against_legacy_book_names(self):
        s_name, s_addr, r_name, r_addr = resolve_wallets(
            SAMPLE, 'w1_osmosis', 'w1_juno'
        )
        self.assertEqual(s_name, 'wallet_1_osmosis')
        self.assertEqual(s_addr, 'osmo1aaa')
        self.assertEqual(r_name, 'wallet_1_juno')
        self.assertEqual(r_addr, 'juno1bbb')

    def test_missing_sender(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_wallets(SAMPLE, 'wallet_missing', 'wallet_1_juno')
        self.assertIn('wallet_missing', str(ctx.exception))

    def test_missing_receiver(self):
        with self.assertRaises(ValueError) as ctx:
            resolve_wallets(SAMPLE, 'wallet_1_osmosis', 'wallet_missing')
        self.assertIn('wallet_missing', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
