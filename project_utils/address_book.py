from typing import List, Tuple


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

    for item in data_address:
        name_wallet = item['name']
        if name_wallet == sender_key:
            sender_name = name_wallet
            sender_address = item['address']
        if name_wallet == receiver_key:
            receiver_name = name_wallet
            receiver_address = item['address']

    if sender_name is None or receiver_name is None:
        missing = []
        if sender_name is None:
            missing.append(sender_key)
        if receiver_name is None:
            missing.append(receiver_key)
        raise ValueError(f'Wallet(s) not found in address book: {", ".join(missing)}')

    return sender_name, sender_address, receiver_name, receiver_address
