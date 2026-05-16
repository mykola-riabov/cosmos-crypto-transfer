# Wallets

`wallets_list.py` создаётся через меню **Check and create data → Generate Wallets list**.

Содержит `LocalWallet` по сетям и функцию `write_address_variables_to_json` для адресной книги.

Мнемоника читается из `source/creds/wallet.json` (см. `chain/wallets/get_creds.py`).

Файл `wallets_list.py` не хранится в git.
