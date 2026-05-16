from typing import Callable, Dict, List, Optional, Tuple


MenuItem = Tuple[str, str, Optional[Callable[[], None]]]


def run_menu(
    title: str,
    items: List[MenuItem],
    *,
    back_label: str = 'Back',
    exit_label: str = 'Exit',
    on_back: Optional[Callable[[], None]] = None,
    allow_exit: bool = True,
) -> str:
    """Run a menu loop. Returns 'back', 'exit', or 'continue'."""
    from colorama import Fore, Style

    while True:
        print(Fore.RED + '################################################' + Style.RESET_ALL)
        print(Fore.GREEN + title + Style.RESET_ALL)
        print(Fore.RED + '################################################' + Style.RESET_ALL)

        for idx, (_, label, _) in enumerate(items, start=1):
            print(f'{idx}. {label}')

        back_idx = len(items) + 1
        exit_idx = len(items) + 2 if allow_exit else None
        print(Fore.YELLOW + f'{back_idx}. {back_label}' + Style.RESET_ALL)
        if allow_exit:
            print(Fore.RED + f'{exit_idx}. {exit_label}' + Style.RESET_ALL)

        choice = input('Enter your choice: ').strip()

        if choice == str(back_idx):
            if on_back:
                on_back()
            return 'back'

        if allow_exit and choice == str(exit_idx):
            return 'exit'

        try:
            choice_idx = int(choice)
        except ValueError:
            print('Invalid choice. Please try again.')
            continue

        if 1 <= choice_idx <= len(items):
            _, _, handler = items[choice_idx - 1]
            if handler:
                handler()
            continue

        print('Invalid choice. Please try again.')
