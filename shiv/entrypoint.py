import os
from sys import argv
from questionary import select

from .core import FileTreeCLUI, RedPrint

ERRORS_TO_QUIT: int = 20

def main() -> None:
    if "-v" in argv:
        RedPrint("Running in -v (verbose) mode", exit_after=False)
    if "-c" in argv:
        RedPrint("Running in -c (colour) mode", exit_after=False)
    errors: list[str] = []
    try:
        ft = FileTreeCLUI(argv[1])
    except IndexError:
        ft = FileTreeCLUI(os.path.abspath(select("Select a location as argument 1:", [i+'/' for i in [
            "."
        ]+os.listdir(".")]).ask()))
    try:
        ft.InitRoot()
    except FileNotFoundError:
        RedPrint(f"'{argv[1]}' is not a valid WorkspaceRoot path.")
        exit()
    while True:
        try:
            ft.Display()
        except Exception as err:
            if "-v" in argv:
                raise err
            RedPrint(f"\n\n\033[31mError: {err}\033[0m\n\n", exit_after=False)
            if errors[-ERRORS_TO_QUIT:-1] == [str(err)]*(ERRORS_TO_QUIT - 1):
                RedPrint(f"Same error occurred {ERRORS_TO_QUIT} times in a row, quitting program now.", exit_after=False)
                exit(1)
            errors.append(str(err))
            continue
        break