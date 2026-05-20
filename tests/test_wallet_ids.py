import unittest

from project_utils.wallet_ids import (
    book_entry_name,
    normalize_wallet_id,
    parse_wallet_attr,
    wallet_id_from_book_name,
)


class TestWalletIds(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_wallet_id('w1'), 'w1')
        self.assertEqual(normalize_wallet_id('wallet_2'), 'w2')
        self.assertEqual(normalize_wallet_id('3'), 'w3')

    def test_book_name(self):
        self.assertEqual(book_entry_name('w2', 'agoric'), 'w2_agoric')
        self.assertEqual(wallet_id_from_book_name('w2_agoric'), 'w2')
        self.assertEqual(wallet_id_from_book_name('wallet_1_osmosis'), 'w1')

    def test_parse_attr(self):
        self.assertEqual(parse_wallet_attr('wallet_1_osmosis_chain'), ('w1', 'osmosis'))
        self.assertEqual(parse_wallet_attr('w2_cosmoshub_chain'), ('w2', 'cosmoshub'))


if __name__ == '__main__':
    unittest.main()
