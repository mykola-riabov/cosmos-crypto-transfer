from typing import List, Tuple

from project_utils.wallet_ids import canonical_book_name


def resolve_wallets(
    data_address: List[dict],
    sender_key: str,
    receiver_key: str,
) -> Tuple[str, str, str, str]:
    """Resolve wallet names to on-chain addresses from address book entries."""
    sender_name = None
    receiver_name = None
    sender_address = None
    receiver_address = None

    sender_canon = canonical_book_name(sender_key)
    receiver_canon = canonical_book_name(receiver_key)

    for item in data_address:
        name_wallet = (item.get('name') or '').strip()
        if not name_wallet:
            continue
        item_canon = canonical_book_name(name_wallet)
        if sender_name is None and (
            name_wallet == sender_key or item_canon == sender_canon
        ):
            sender_name = name_wallet
            sender_address = item.get('address') or ''
        if receiver_name is None and (
            name_wallet == receiver_key or item_canon == receiver_canon
        ):
            receiver_name = name_wallet
            receiver_address = item.get('address') or ''

    if sender_name is None or receiver_name is None:
        missing = []
        if sender_name is None:
            missing.append(sender_key)
        if receiver_name is None:
            missing.append(receiver_key)
        raise ValueError(f'Wallet(s) not found in address book: {", ".join(missing)}')

    return sender_name, sender_address, receiver_name, receiver_address
