import unittest

from gui.autocomplete import (
    filter_token_values,
    prefix_matches,
    resolve_combobox_value,
    token_matches,
)

CANDIDATES = [
    'OSMO — uosmo',
    'OSMO — ibc/other-osmo-denom',
    'USDC — ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4',
    'ATOM — ibc/27394FB092D2ECCD56123C74F36E4C1F926001CEADA9CA97EA622B25F41E5EB2',
]


class TestAutocomplete(unittest.TestCase):
    def test_prefix_filter_os(self):
        out = filter_token_values(CANDIDATES, 'os')
        self.assertEqual(len(out), 2)
        self.assertTrue(all('OSMO' in v for v in out))
        self.assertNotIn(CANDIDATES[2], out)

    def test_prefix_case_insensitive(self):
        out = filter_token_values(CANDIDATES, 'OS')
        self.assertEqual(len(out), 2)

    def test_no_substring_match_in_denom(self):
        self.assertFalse(token_matches(CANDIDATES[2], 'mo'))

    def test_filter_by_denom_substring(self):
        out = filter_token_values(CANDIDATES, '498a0751')
        self.assertEqual(out, [CANDIDATES[2]])

    def test_resolve_by_denom_fragment(self):
        self.assertEqual(
            resolve_combobox_value('ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4', CANDIDATES),
            CANDIDATES[2],
        )

    def test_resolve_unique_ticker(self):
        self.assertEqual(resolve_combobox_value('atom', CANDIDATES), CANDIDATES[3])

    def test_resolve_ambiguous_prefix(self):
        self.assertIsNone(resolve_combobox_value('os', CANDIDATES))
        self.assertEqual(len(filter_token_values(CANDIDATES, 'os')), 2)
        self.assertEqual(len(prefix_matches('os', CANDIDATES)), 0)


if __name__ == '__main__':
    unittest.main()
