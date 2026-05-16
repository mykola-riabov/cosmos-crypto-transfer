# cosmos-crypto-transfer

CLI для **IBC-переводов** между сетями Cosmos, просмотра балансов и адресной книги. Использует **таймаут по времени** (по умолчанию 120 с), а не по высоте блока — удобнее для арбитража, чем многие кошельки.

## Репозиторий и локальные данные

Код живёт в этом git-репозитории. **Секреты и тяжёлые данные — снаружи**, в каталоге `source/` рядом с проектом (по умолчанию `../source` от корня репозитория). В git не попадают:

| Путь (вне репо) | Содержимое |
|-----------------|------------|
| `source/creds/wallet.json` | мнемоника (только у вас на диске) |
| `source/data/` | address book, mapping, cosmos_data_list |
| `source/chain-registry/` | клон [chain-registry](https://github.com/cosmos/chain-registry) |
| `source/temp/` | логи, промежуточные JSON |

Так можно спокойно делать `git push` без риска утечки seed-фразы.

```
mygit/
├── cosmos-crypto-transfer/    ← этот репозиторий (код, config, tests)
└── source/                    ← локально, в .gitignore
    ├── creds/wallet.json
    ├── data/
    └── ...
```

## Требования

- Linux
- Python 3.10+
- Git, pip

## Установка

```bash
git clone <repo-url> cosmos-crypto-transfer
cd cosmos-crypto-transfer

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m unittest discover -s tests -v   # без мнемоники
```

## Первый запуск

```bash
python menu_crypto.py
```

Рекомендуемая последовательность в меню **«3. Check and create data»**:

| Шаг | Пункт | Действие |
|-----|-------|----------|
| 1 | 1 | Создать `source/`, клонировать chain-registry |
| 2 | 4 | Проверить зависимости (`requirements.txt`) |
| 3 | 6 | Собрать `cosmos_data_list.json` |
| 4 | 7 | Сгенерировать `chain/clients/ledger_clients.py` |
| 5 | 8 | Сгенерировать `chain/wallets/wallets_list.py` |
| 6 | 9 | Сгенерировать `source/data/address_book.json` |

Запускайте **`python menu_crypto.py`** из корня репозитория — `PYTHONPATH` настраивается автоматически.

## Учётные данные

1. Скопируйте шаблон:
   ```bash
   mkdir -p ../source/creds
   cp config/wallet.example.json ../source/creds/wallet.json
   chmod 600 ../source/creds/wallet.json
   ```
2. Впишите мнемонику в поле `mnemonic_wallet_1` (или `mnemonic`).
3. **Не коммитьте** `wallet.json` — он уже в `.gitignore`.

Для сетей с нестандартным HD-path (например **Agoric**, slip44 `564`) укажите `"slip44": 564` в записи сети в `cosmos_data_list.json` перед шагом 8.

## Переменные окружения

См. `.env.example`:

| Переменная | По умолчанию |
|------------|----------------|
| `COSMOS_PROJECT_ROOT` | каталог с `menu_crypto.py` |
| `COSMOS_SOURCE_PATH` | `../source` |
| `COSMOS_WALLET_FILE` | `source/creds/wallet.json` |

## Структура репозитория

```
cosmos-crypto-transfer/
├── menu_crypto.py
├── menu/
├── action_crypto/          # балансы, IBC, Osmosis DEX info
├── config/
│   ├── ibc_routes.json     # маршруты IBC (редактируемый)
│   └── wallet.example.json # шаблон creds (без реальной фразы)
├── addresses/              # denoms_book, pools_book
├── chain/
│   ├── clients/            # ledger_clients.py — генерируется
│   └── wallets/            # wallets_list.py — генерируется
├── project_utils/
└── tests/
```

## IBC-маршруты

Все маршруты в `config/ibc_routes.json`. Пример:

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

Перевод: меню **1 → 4**, выбор сети и маршрута, символ и сумма из `denoms_book.json`.

## Тесты

```bash
python -m unittest discover -s tests -v
```

Не требуют `wallet.json` и доступа к блокчейну.

## Перед `git push`

- [ ] Нет файла `wallet.json` в репозитории
- [ ] Нет `chain/clients/ledger_clients.py` и `chain/wallets/wallets_list.py` в коммите
- [ ] В коде и коммитах нет мнемоники (только `wallet.example.json` с заглушками)
- [ ] `../source/` не добавлен в git

## Скриншоты

Каталог `screen/` — примеры интерфейса.
