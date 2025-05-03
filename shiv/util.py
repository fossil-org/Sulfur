import random, os
from sys import argv
from pathlib import Path
from importlib import import_module

from .shivim import run

def RedPrint(*s: str, sep: str = " ", exit_after: bool = True) -> None:
    if exit_after:
        raise Exception(f"\033[91m{sep.join(s)}\033[0m")
    else:
        print(f"\033[91m{sep.join(s)}\033[0m")
def GreenPrint(*s: str, sep: str = " ") -> None:
    print(f"\033[92m{sep.join(s)}\033[0m")
def GetCharVariant(order: int) -> str:
    return f"0{order}" if len(str(order)) == 1 else str(order)
def GetRandomColor(text: str) -> str:
    if "-c" not in argv:
        return text
    r: int = random.randint(80, 255)
    g: int = random.randint(80, 255)
    b: int = random.randint(80, 255)

    ansi_code: str = f"\033[38;2;{r};{g};{b}m"

    return f"{ansi_code}{text}\033[0m"

try:
    from questionary import select
except ModuleNotFoundError:
    RedPrint("Unfulfilled dependency: questionary", exit_after=False)
    exit(1)

def RunShivim(file_name: str) -> None:
    with open(str(Path(file_name).parent / "__Type__")) as file:
        file_type: str = file.read()
    if file_type == "Boolean":
        with open(file_name, "w") as file:
            file.write(select("Select a boolean value:", ["true", "false"]).ask())
    elif file_type == "Integer":
        while True:
            from . import GetVF, Require
            q: str = input("\033[91mEnter an integer value: \033[0m")
            try:
                evq = eval(q, {
                    "shiv": import_module(".", __package__),
                    "this": GetVF(os.path.join(file_name, "__Content__")),
                    "require": Require
                })
            except Exception:
                RedPrint("Invalid integer value.", exit_after=False)
                continue
            if not isinstance(evq, int):
                RedPrint("Invalid integer value.", exit_after=False)
                continue
            with open(file_name, "w") as file:
                file.write(str(evq))
            break
    elif file_type == "Float":
        while True:
            from . import GetVF, Require
            q: str = input("\033[91mEnter an float value: \033[0m")
            try:
                evq = eval(q, {
                    "shiv": import_module(".", __package__),
                    "this": GetVF(os.path.join(file_name, "__Content__")),
                    "require": Require
                })
            except Exception:
                RedPrint("Invalid float value.", exit_after=False)
                continue
            if not isinstance(evq, float):
                RedPrint("Invalid float value.", exit_after=False)
                continue
            with open(file_name, "w") as file:
                file.write(str(evq))
            break
    elif file_type not in ["Folder", "Class", "ValueList", "WorkspaceRoot"]:
        run(file_name)
    else:
        with open(file_name, "w") as file:
            file.write("")