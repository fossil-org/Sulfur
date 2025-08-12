import os, ctypes, sys
from sys import argv
from questionary import select

from .core import ObjectTreeCLUI
from .util import RedPrint, SEP, GreenPrint

ERRORS_TO_QUIT: int = 5

def IsAdmin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception: # NOQA
        return False


def main() -> None:
    # if not IsAdmin():
    #     ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    #     sys.exit()
    if "-v" in argv:
        RedPrint("Running in -v (verbose) mode", exit_after=False)
    if "-c" in argv:
        RedPrint("Running in -c (colour) mode", exit_after=False)
    if "-e" in argv:
        RedPrint("Running in -e (eval preview) mode", exit_after=False)
        print("\033[33mWARNING: This mode executes all ScriptEval objects every time the clui is refreshed. Malicious or broken code may damage or crash sulfur.\033[0m")
    if "-n" in argv:
        RedPrint("Running in -n (no permissions) mode", exit_after=False)
        print("\033[33mWARNING: Some commands may not render correctly in -n mode.\033[0m")
    errors: list[str] = []
    try:
        if argv[1].startswith("-"):
            raise IndexError("This error is raised to make -options not behave like workspace paths.")
        ft = ObjectTreeCLUI(argv[1])
    except IndexError:
        selection: str = select("Select a location as argument 1:", [i+'/' for i in [
            "."
        ]+os.listdir(".")]).ask()
        if selection is None:
            exit(0)
        ft = ObjectTreeCLUI(os.path.abspath(selection))
    try:
        ft.InitRoot()
    except FileNotFoundError:
        RedPrint(f"'{argv[1]}' is not a valid Workspace path.")
        exit()
    while True:
        try:
            ft.Display(viewer_mode="-n" in argv)
        except PermissionError as err:
            if "-v" in argv:
                raise err
            RedPrint("Ran into PermissionError. The action you have performed may require administrator permissions on your pc.\nConsider rerunning Sulfur as an administrator.")
        except Exception as err:
            if "-v" in argv:
                raise err
            if errors[-ERRORS_TO_QUIT:-1] == [str(err)]*(ERRORS_TO_QUIT - 1):
                if ERRORS_TO_QUIT != 1:
                    RedPrint(f"Same error occurred {ERRORS_TO_QUIT} times in a row, quitting program now.", exit_after=False)
                exit(1)
            RedPrint(f"Error: {err}", exit_after=False)
            errors.append(str(err))
            continue
        break