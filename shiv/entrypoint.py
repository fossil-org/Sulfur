from sys import argv

from .core import FileTreeCLUI

def main() -> None:
    try:
        ft = FileTreeCLUI(argv[1])
    except IndexError:
        print("Usage: shiv (WorkspaceRoot path).")
        exit()
    try:
        ft.initRoot()
    except FileNotFoundError:
        print(f"'{argv[1]}' is not a valid WorkspaceRoot path.")
        exit()
    ft.display()