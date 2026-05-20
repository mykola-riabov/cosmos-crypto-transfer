import json
import unittest
from unittest.mock import patch

from action_crypto.tx.swap.skip_swap import (
    build_transaction_from_skip_msgs,
    prepare_skip_swap,
)
from project_utils.skip_client import SkipApiError

SAMPLE_ADDRESS_BOOK = [
    {'name': 'w1_osmosis', 'network': 'osmosis', 'address': 'osmo1x8ad0zyw52mvndh7hlnafrg0gt284ga7syxplu'},
]

SAMPLE_ROUTE = {
    'source_asset_denom': 'uosmo',
    'source_asset_chain_id': 'osmosis-1',
    'dest_asset_denom': 'ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4',
    'dest_asset_chain_id': 'osmosis-1',
    'amount_in': '1000000',
    'estimated_amount_out': '62404',
    'operations': [
        {
            'swap': {
                'swap_in': {
                    'swap_operations': [{'pool': '1221', 'denom_in': 'uosmo', 'denom_out': 'ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4'}],
                },
            },
        },
    ],
    'txs_required': 1,
    'swap_price_impact_percent': '1.0',
}

SAMPLE_MSGS = {
    'min_amount_out': '61468',
    'txs': [
        {
            'cosmos_tx': {
                'chain_id': 'osmosis-1',
                'signer_address': 'osmo1x8ad0zyw52mvndh7hlnafrg0gt284ga7syxplu',
                'msgs': [
                    {
                        'msg_type_url': '/cosmwasm.wasm.v1.MsgExecuteContract',
                        'msg': json.dumps({
                            'sender': 'osmo1x8ad0zyw52mvndh7hlnafrg0gt284ga7syxplu',
                            'contract': 'osmo10a3k4hvk37cc4hnxctw4p95fhscd2z6h2rmx0aukc6rm8u9qqx9smfsh7u',
                            'msg': {'swap_and_action': {'user_swap': {}}},
                            'funds': [{'denom': 'uosmo', 'amount': '1000000'}],
                        }),
                    },
                ],
            },
        },
    ],
}


class TestSkipSwap(unittest.TestCase):
    def test_build_transaction_from_skip_msgs(self):
        tx = build_transaction_from_skip_msgs(
            SAMPLE_MSGS,
            chain_id='osmosis-1',
            signer_address='osmo1x8ad0zyw52mvndh7hlnafrg0gt284ga7syxplu',
        )
        self.assertEqual(len(tx.msgs), 1)

    @patch('action_crypto.tx.swap.skip_swap.fetch_msgs', return_value=SAMPLE_MSGS)
    @patch('action_crypto.tx.swap.skip_swap.fetch_route', return_value=SAMPLE_ROUTE)
    @patch('action_crypto.tx.swap.skip_swap._resolve_denoms')
    def test_prepare_skip_swap_mocked(self, mock_denoms, _mock_route, _mock_msgs):
        mock_denoms.return_value = (
            'uosmo',
            6,
            'ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4',
            6,
        )
        import tempfile
        import os

        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(SAMPLE_ADDRESS_BOOK, f)
            book_path = f.name
        try:
            preview = prepare_skip_swap(
                'OSMO',
                'USDC',
                1.0,
                book_path,
                '/dev/null',
                'w1_osmosis',
                'w1_osmosis_chain',
                slippage_percent=1.5,
            )
            self.assertEqual(preview.symbol_in, 'OSMO')
            self.assertEqual(preview.pool_ids, ['1221'])
            self.assertEqual(len(preview.transaction.msgs), 1)
        finally:
            os.unlink(book_path)

    @patch('action_crypto.tx.swap.skip_swap.fetch_route', side_effect=SkipApiError('no route'))
    @patch('action_crypto.tx.swap.skip_swap._resolve_denoms')
    def test_prepare_raises_skip_error(self, mock_denoms, _mock_route):
        mock_denoms.return_value = ('uosmo', 6, 'uatom', 6)
        import tempfile
        import os

        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(SAMPLE_ADDRESS_BOOK, f)
            book_path = f.name
        try:
            with self.assertRaises(SkipApiError):
                prepare_skip_swap(
                    'OSMO',
                    'ATOM',
                    1.0,
                    book_path,
                    '/dev/null',
                    'w1_osmosis',
                    'w1_osmosis_chain',
                )
        finally:
            os.unlink(book_path)


if __name__ == '__main__':
    unittest.main()
