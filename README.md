# cosmos-crypto-transfer

Cosmos wallet toolkit: **IBC transfers**, **Osmosis swaps** (Skip API routing + local signing), balances, address book, and token catalog. Available as a **desktop GUI** (tkinter) or **CLI** (`menu_crypto.py` / `cosmos_cli.py`).

IBC transfers use a **time-based timeout** (default 120 seconds) instead of a block-height timeout, which is often better for arbitrage than typical wallets.

**Credentials:** mnemonic lives only in a **KeePass vault** under `~/.market_ai_secrets/` (not in the repo). Local setup artifacts go under `source/` (gitignored).

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

| Path | Contents |
|------|----------|
| `./source/` (inside repo, gitignored) | address book, client mapping, chain-registry clones, logs |
| `~/.market_ai_secrets/cosmos-crypto-transfer/` | **KeePass vault** — `wallet.kdbx`, `wallet.key`, `master.password` |

The mnemonic is stored **only** in the encrypted KeePass database. Copy `wallet.key` and `master.password` from a USB stick when you trade; delete those two files locally when idle. The database file can stay on disk (it remains encrypted).

Override the secrets folder name with `MARKET_AI_SECRETS_SLUG` (default: `cosmos-crypto-transfer`).

```
cosmos-crypto-transfer/          ← git repo
├── source/                      ← local data (.gitignore)
│   ├── data/
│   └── chain-registry/
└── ...

~/.market_ai_secrets/
└── cosmos-crypto-transfer/      ← never in git
    ├── wallet.kdbx
    ├── wallet.key
    └── master.password
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

1. Install dependencies (see [Install](#install)).
2. Create the **secret vault** (GUI: Setup → Secret vault, or `python secrets_cli.py init`).
3. Run **Setup** (GUI tab or CLI menu “Check and create data”) to build `source/data/` and generated chain files.

**Interactive text menu (full setup + actions):**

```bash
python menu_crypto.py
```

**Headless CLI** (SSH, scripts; no tkinter):

```bash
./run_cli.sh status
./run_cli.sh setup pipeline
./run_cli.sh balances
./run_cli.sh transfer preview -s osmosis -d cosmoshub --symbol osmo --amount 0.01
# same as: python cosmos_cli.py …
```

**GUI** (tkinter, Linux desktop):

```bash
# Debian/Ubuntu if tkinter is missing:
# sudo apt install python3-tk

./run_gui.sh
# or: python gui_crypto.py
```

Quick start without venv:

```bash
pip3 install -r requirements.txt
python3 gui_crypto.py
```

| GUI tab | Purpose |
|---------|---------|
| Portfolio | Wallet overview; **Name token…** for unknown IBC denoms |
| Send | IBC transfer (routes, preview, time/block timeout, gas) |
| Swap | Osmosis same-chain swap: [Skip API](https://docs.skip.build/go/general/getting-started) quote/route, Cosmpy sign/broadcast |
| Receive | Deposit addresses per enabled network |
| History | Transfer attempt log |
| Networks | Enable/disable chains, REST health |
| Tokens | chain-registry asset list (+ Osmosis prices when available) |
| Denoms | Edit `addresses/denoms/denoms_book.json` (symbol ↔ on-chain denom) |
| Market | Osmosis DEX token prices |
| Address book | Derived addresses (from vault mnemonic) |
| Setup | Same steps as CLI “Check and create data”; **Run first-time setup** |
| Settings | Theme (dark/light); prefs in `source/data/gui_settings.json` |
| Status | Vault, generated clients, address book readiness |

**Token symbols** for Send/Portfolio come from `addresses/denoms/denoms_book.json` (plus registry/Keplr data loaded into the catalog). Manual names and auto-resolved IBC denoms are stored in that file.

GUI IBC sends use `prepare_ibc_transfer` / `broadcast_ibc_transfer` (no terminal prompts).

**Swap (Osmosis):** Preview calls Skip `/v2/fungible/route` then `/v2/fungible/msgs`; the app builds `MsgExecuteContract` messages and signs with your vault wallet (same flow as Send). Requires Osmosis enabled and a funded address. Optional env: `SKIP_API_URL` (default `https://api.skip.build`). Only single-tx same-chain routes are supported in this version.

Recommended flow under **“3. Check and create data”** (CLI) or the **Setup** tab (GUI):

| Step | Menu item | Action |
|------|-----------|--------|
| 1 | 1 | Create `source/`, clone chain-registry |
| 2 | 4 | Install dependencies (`requirements.txt`) |
| 3 | 6 | Build `cosmos_data_list.json` |
| 4 | 7 | Generate `chain/clients/ledger_clients.py` |
| 5 | 8 | Generate `chain/wallets/wallets_list.py` |
| 6 | 9 | Generate `source/data/address_book.json` |

Run **`python menu_crypto.py`** from the repository root; `PYTHONPATH` is set automatically.

## Secret vault (KeePass)

**GUI:** Setup → **Create / reset vault** (also offered at the start of first-time setup).

**CLI:**

```bash
python secrets_cli.py init          # create vault + key file + master.password
python secrets_cli.py status
python secrets_cli.py show          # summary only
python secrets_cli.py set           # change mnemonic
```

Files are created under `~/.market_ai_secrets/cosmos-crypto-transfer/`.

For chains with a non-default HD path (e.g. **Agoric**, slip44 `564`), add `"slip44": 564` to that chain’s entry in `cosmos_data_list.json` before step 8.

## Environment variables

See `.env.example`:

| Variable | Default |
|----------|---------|
| `COSMOS_PROJECT_ROOT` | directory containing `menu_crypto.py` |
| `COSMOS_SOURCE_PATH` | `<project>/source` |
| `MARKET_AI_SECRETS_SLUG` | `cosmos-crypto-transfer` |

## Project layout

```
cosmos-crypto-transfer/
├── menu_crypto.py          # interactive text menu
├── cosmos_cli.py           # headless CLI entry
├── gui_crypto.py           # GUI entry
├── secrets_cli.py          # KeePass vault (init / set mnemonic)
├── run_gui.sh / run_cli.sh
├── gui/
├── cli/
├── menu/
├── action_crypto/          # balances, IBC, Osmosis DEX info
├── config/
│   └── ibc_routes.json     # IBC routes (editable, in git)
├── addresses/
│   └── denoms/denoms_book.json   # token map (in git; edit via Denoms tab)
├── chain/
│   ├── clients/            # ledger_clients.py — generated, gitignored
│   └── wallets/            # wallets_list.py — generated, gitignored
├── source/                 # local only (.gitignore): data/, chain-registry/, …
├── project_utils/
├── screen/                 # UI screenshots
└── tests/
```

**Not pushed to GitHub:** everything under `source/`, generated `ledger_clients.py` / `wallets_list.py`, vault files in `~/.market_ai_secrets/`, `gui_settings.json`, any `wallet.json` if present.

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

To transfer: CLI menu **1 → 4**, or GUI **Send** tab; pick source/destination networks and route, then token and amount (symbols from `denoms_book.json`).

## Tests

```bash
python -m unittest discover -s tests -v
```
