# cosmos-crypto-transfer

CLI for **IBC token transfers** across Cosmos chains, balance checks, and address book management. Uses a **time-based timeout** (default 120 seconds) instead of a block-height timeout, which is often better for arbitrage than typical wallets.

## Screenshots

Main menu:

![main menu](screen/main.png)

Address book:

![address book](screen/book.png)

Osmosis DEX token info:

![token prices](screen/price.png)

Actions menu:

![actions](screen/action.png)

IBC transfer:

![transfer](screen/transfer.png)

## Repository vs local data

Application code lives in this git repository. **Secrets and heavy data stay outside** the repo, in a `source/` directory next to the project (default: `../source` relative to the repo root):

| Path (outside repo) | Contents |
|-------------------|----------|
| `source/creds/wallet.json` | mnemonic (local only) |
| `source/data/` | address book, client mapping, cosmos_data_list |
| `source/chain-registry/` | clone of [chain-registry](https://github.com/cosmos/chain-registry) |
| `source/temp/` | logs, intermediate JSON |

This keeps `git push` safe: no seed phrase in the repository.

```
mygit/
├── cosmos-crypto-transfer/    ← this repo (code, config, tests)
└── source/                    ← local only (.gitignore)
    ├── creds/wallet.json
    ├── data/
    └── ...
```

## Requirements

- Linux
- Python 3.10+
- Git, pip

## Install

```bash
git clone <repo-url> cosmos-crypto-transfer
cd cosmos-crypto-transfer

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m unittest discover -s tests -v   # no mnemonic required
```

## First run

```bash
python menu_crypto.py
```

Recommended flow under **“3. Check and create data”**:

| Step | Menu item | Action |
|------|-----------|--------|
| 1 | 1 | Create `source/`, clone chain-registry |
| 2 | 4 | Install dependencies (`requirements.txt`) |
| 3 | 6 | Build `cosmos_data_list.json` |
| 4 | 7 | Generate `chain/clients/ledger_clients.py` |
| 5 | 8 | Generate `chain/wallets/wallets_list.py` |
| 6 | 9 | Generate `source/data/address_book.json` |

Run **`python menu_crypto.py`** from the repository root; `PYTHONPATH` is set automatically.

## Credentials

1. Copy the template:
   ```bash
   mkdir -p ../source/creds
   cp config/wallet.example.json ../source/creds/wallet.json
   chmod 600 ../source/creds/wallet.json
   ```
2. Set your mnemonic in `mnemonic_wallet_1` (or `mnemonic`).
3. **Never commit** `wallet.json` — it is listed in `.gitignore`.

For chains with a non-default HD path (e.g. **Agoric**, slip44 `564`), add `"slip44": 564` to that chain’s entry in `cosmos_data_list.json` before step 8.

## Environment variables

See `.env.example`:

| Variable | Default |
|----------|---------|
| `COSMOS_PROJECT_ROOT` | directory containing `menu_crypto.py` |
| `COSMOS_SOURCE_PATH` | `../source` |
| `COSMOS_WALLET_FILE` | `source/creds/wallet.json` |

## Project layout

```
cosmos-crypto-transfer/
├── menu_crypto.py
├── menu/
├── action_crypto/          # balances, IBC, Osmosis DEX info
├── config/
│   ├── ibc_routes.json     # IBC routes (editable)
│   └── wallet.example.json # creds template (placeholders only)
├── addresses/              # denoms_book, pools_book
├── chain/
│   ├── clients/            # ledger_clients.py — generated
│   └── wallets/            # wallets_list.py — generated
├── project_utils/
├── screen/                 # UI screenshots
└── tests/
```

## IBC routes

All routes are defined in `config/ibc_routes.json`. Example:

```json
{
  "source_network": "agoric",
  "destination_network": "osmosis",
  "sender_wallet": "wallet_1_agoric",
  "receiver_wallet": "wallet_1_osmosis",
  "channel": "channel-1",
  "gas": 200000,
  "timeout_seconds": 120,
  "client_attr": "agoric_client",
  "wallet_attr": "wallet_1_agoric_chain"
}
```

To transfer: menu **1 → 4**, pick source chain and route, then symbol and amount from `denoms_book.json`.

## Tests

```bash
python -m unittest discover -s tests -v
```

No `wallet.json` or live chain access required.

## Before `git push`

- [ ] No `wallet.json` in the repository
- [ ] No generated `ledger_clients.py` or `wallets_list.py` in commits
- [ ] No real mnemonic in code (only placeholders in `wallet.example.json`)
- [ ] `../source/` is not tracked by git
