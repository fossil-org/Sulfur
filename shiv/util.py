import random, os, keyword
from sys import argv
from pathlib import Path
from importlib import import_module
from typing import Callable
from readchar import readchar
from questionary import select

from .shivim import Run

def RedPrint(*s: str, sep: str = " ", exit_after: bool = True) -> None:
    if exit_after:
        raise Exception(f"\033[91m{sep.join(s)}\033[0m")
    else:
        print(f"\033[91m{sep.join(s)}\033[0m")
def GreenPrint(*s: str, sep: str = " ") -> None:
    print(f"\033[92m{sep.join(s)}\033[0m")
def GetCharVariant(order: int) -> str:
    return f"0{order}" if len(str(order)) == 1 else str(order)
def GetRandomColor(text: str, force: bool = False) -> str:
    if "-c" not in argv and not force:
        return text
    r: int = random.randint(80, 255)
    g: int = random.randint(80, 255)
    b: int = random.randint(80, 255)

    ansi_code: str = f"\033[38;2;{r};{g};{b}m"

    return f"{ansi_code}{text}\033[0m"

PY_KWS: list[str] = keyword.kwlist + keyword.softkwlist + ["..."]
HIGHLIGHTS: dict[str] = {
    "Script": PY_KWS,
    "ScriptModule": PY_KWS,
    "ScriptEval": PY_KWS,
    "ShellScript": ["echo", "cd", "mkdir", "sudo", "pip", "py", "python", "python3", "shiv", "rmdir", "rm", "cp", "mv", "venv", "which", "git", "gh"]
}
GetHighlight: Callable = lambda t: HIGHLIGHTS.get(t, [])
OBJECT_TYPE_LIST: list[str] = [
    "Script",
    "ScriptModule",
    "Folder",
    "ValueList",
    "State",
    "WholeNumber",
    "DecimalNumber",
    "Text",
    "ScriptEval",
    "Character",
    "ShellScript",
    "Color",
    "URL",
    "Class"
]
ANSI_COLORS: dict[int, str] = {
    30: "Black",
    31: "Red",
    32: "Green",
    33: "Yellow",
    34: "Blue",
    35: "Magenta",
    36: "Cyan",
    37: "White",
    90: "Bright Black (Gray)",
    91: "Bright Red",
    92: "Bright Green",
    93: "Bright Yellow",
    94: "Bright Blue",
    95: "Bright Magenta",
    96: "Bright Cyan",
    97: "Bright White"
}
def RunShivim(file_name: str, highlights: list[str]) -> None:
    with open(str(Path(file_name).parent / "__Type__")) as file:
        file_type: str = file.read()
    if file_type == "State":
        with open(file_name, "w") as file:
            file.write(select("Select a boolean value:", ["true", "false"]).ask())
    elif file_type == "Color":
        color: str = input("\033[91mChoose a color (ANSI), run [hc] for help: \033[0m")
        with open(file_name, "w") as file:
            color = str(list(ANSI_COLORS.keys())[int(list(ANSI_COLORS.values()).index(color.capitalize()))] if color.capitalize() in ANSI_COLORS.values() else color)
            file.write(color + "#" + eval(f"'\\033[{color}m'"))
    elif file_type == "URL":
        url: str = input("\033[91mEnter a URL: \033[0m")
        url = f"https://{url}" if "://" not in url else url
        with open(file_name, "w") as file:
            file.write(url)
    elif file_type == "Character":
        while True:
            RedPrint("Enter one character (esc to cancel):", exit_after=False)
            char: str = readchar()
            if char == "\x1b":
                break
            print(f"Is this correct?: {'\\n' if char == '\n' else char} (y/n)")
            while True:
                confirm: str = readchar()
                if confirm == "y":
                    with open(file_name, "w") as file:
                        file.write(char)
                    return
                elif confirm == "n":
                    break
    elif file_type == "WholeNumber":
        while True:
            from . import GetVF, Require
            q: str = input("\033[91mEnter an integer value: \033[0m").replace(" ", "")
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
    elif file_type == "DecimalNumber":
        while True:
            from . import GetVF, Require
            q: str = input("\033[91mEnter an float value: \033[0m").replace(" ", "").replace(",", ".")
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
    elif file_type not in ["Folder", "Class", "ValueList", "Workspace"]:
        Run(file_name, highlights)
    else:
        with open(file_name, "w") as file:
            file.write("")