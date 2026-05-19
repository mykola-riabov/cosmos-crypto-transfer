# Wallets

`wallets_list.py` создаётся через меню **Check and create data → Generate Wallets list** (или Setup в GUI).

Содержит `LocalWallet` по сетям и функцию `write_address_variables_to_json` для адресной книги.

Мнемоника читается только из **KeePass vault** (`~/.market_ai_secrets/<slug>/`, см. `chain/wallets/secret_vault.py` и `get_creds.py`).

Файл `wallets_list.py` не хранится в git.
