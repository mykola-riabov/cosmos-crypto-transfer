import os


def clear_menu(action):
    clear_screen = action
    if clear_screen:
        os.system('cls' if os.name == 'nt' else 'clear')
