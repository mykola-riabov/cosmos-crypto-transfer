import unittest
from pathlib import Path

from project_utils.denoms_lookup import convert_amount, load_denoms_index, resolve_denom

DENOMS = Path(__file__).resolve().parents[1] / 'addresses' / 'denoms' / 'denoms_book.json'


class TestDenomsLookup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = load_denoms_index(str(DENOMS))

    def test_resolve_osmo_osmosis(self):
        denom, decimals = resolve_denom(self.index, 'osmo', 'osmosis')
        self.assertEqual(denom, 'uosmo')
        self.assertEqual(decimals, 6)

    def test_resolve_case_insensitive(self):
        denom, _ = resolve_denom(self.index, 'OSMO', 'Osmosis')
        self.assertEqual(denom, 'uosmo')

    def test_missing_pair_raises(self):
        with self.assertRaises(ValueError):
            resolve_denom(self.index, 'nonexistent_token_xyz', 'osmosis')

    def test_convert_amount(self):
        self.assertEqual(convert_amount(1.5, 6), 1_500_000)
        self.assertEqual(convert_amount(0.000001, 6), 1)


if __name__ == '__main__':
    unittest.main()
