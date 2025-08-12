import random, os, keyword, stat, re
from sys import argv
from pathlib import Path
from importlib import import_module
from typing import Any, Callable
from readchar import readchar
from questionary import select

from .editor import Run
from .pcl import Plugin

SEP: str = "\\" if os.name == "nt" else "/"

def RedPrint(*s: str, sep: str = " ", exit_after: bool = True) -> None:
    print(f"\033[91m{sep.join([str(i) for i in s])}\033[0m")
    if exit_after:
        exit(1)

def GreenPrint(*s: str, sep: str = " ") -> None:
    print(f"\033[92m{sep.join([str(i) for i in s])}\033[0m")
def GetCharVariant(order: int) -> str:
    return f"0{order}" if len(str(order)) == 1 else str(order)
def GetRandomColor(text: str, force: bool = False, minimum_brightness: int = 80, maximum_brightness: int = 255) -> str:
    if "-c" not in argv and not force:
        return text
    r: int = random.randint(minimum_brightness, maximum_brightness)
    g: int = random.randint(minimum_brightness, maximum_brightness)
    b: int = random.randint(minimum_brightness, maximum_brightness)

    ansi_code: str = f"\033[38;2;{r};{g};{b}m"

    return f"{ansi_code}{text}\033[0m"
def ForceRemove(func, path, _):
    """DO NOT CALL. ONLY USE LIKE THIS: shutil.rmtree(..., onerror=ForceRemove)"""
    os.chmod(path, stat.S_IWRITE)
    func(path)
def LenNoColor(text: str) -> int:
    return len(re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text))

PY_KWS: list[str] = keyword.kwlist + keyword.softkwlist + ["..."]
HIGHLIGHTS: dict[str, list[str]] = {
    "Script": PY_KWS,
    "ScriptModule": PY_KWS,
    "ScriptEval": PY_KWS,
    "ShellScript": ["echo", "cd", "mkdir", "sudo", "pip", "py", "python", "python3", "sulfur", "rmdir", "rm", "cp", "mv", "venv", "which", "git", "gh"]
}
GetHighlight: Callable = lambda t: HIGHLIGHTS.get(t) or []
OBJECT_TYPE_LIST: list[str] = [
    "Script",
    "ScriptModule",
    "Folder",
    "ValueArray",
    "Boolean",
    "Integer",
    "Double",
    "String",
    "ScriptEval",
    "Character",
    "ShellScript",
    "Color",
    "URL",
    "Class"
]
for plugin in Plugin.GetEnabledPlugins():
    OBJECT_TYPE_LIST += plugin.GetObjectTypes()
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
def RunEditor(file_name: str, highlights: list[str]) -> None:
    if file_name == "__Content__":
        return
    ea: bool = True
    with open(str(Path(file_name).parent / "__Type__")) as file:
        file_type: str = file.read()
        if ":" in file_type:
            ea = (Plugin.ReadConfig(Plugin.TraceObjectType(file_type))["Editor"] or {}).get("Enabled", True)
            file_type = (Plugin.ReadConfig(Plugin.TraceObjectType(file_type))["Editor"] or {}).get("InheritsFrom") or "UnknownType"
    if ea:
        if file_type == "Boolean":
            with open(file_name, "w") as file:
                file.write(select("Select a boolean value:", ["true", "false"]).ask())
        elif file_type == "Color":
            color: str = input("\033[91mChoose a color (ANSI), run [hc] for help: \033[0m")
            with open(file_name, "w") as file:
                color = str(list(ANSI_COLORS.keys())[int(list(ANSI_COLORS.values()).index(color.capitalize()))] if color.capitalize() in ANSI_COLORS.values() else color)
                file.write(color + "#" + f"'\\033[{color}m'")
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
        elif file_type == "Integer":
            while True:
                from . import GetObject, Require
                q: str = input("\033[91mEnter an integer value: \033[0m").replace(" ", "")
                try:
                    evq = eval(q, {
                        "this": GetObject(os.path.join(file_name, "__Content__")).GetParent(),
                        "print": lambda *_, **__: RedPrint("Error: Cannot use 'print' here.", exit_after=False)
                    })
                except Exception as err:
                    if "-v" in argv:
                        print(f"Eval error ({err.__class__.__name__}): {err}")
                    RedPrint("Invalid integer value.", exit_after=False)
                    continue
                if not isinstance(evq, int):
                    RedPrint("Invalid integer value.", exit_after=False)
                    continue
                with open(file_name, "w") as file:
                    file.write(str(evq))
                break
        elif file_type == "Double":
            while True:
                from . import GetObject, Require
                q: str = input("\033[91mEnter an float value: \033[0m").replace(" ", "").replace(",", ".")
                try:
                    evq = eval(q, {
                        "this": GetObject(os.path.join(file_name, "__Content__")).GetParent(),
                        "print": lambda *_, **__: RedPrint("Error: Cannot use 'print' here.", exit_after=False)
                    })
                except Exception:
                    if "-v" in argv:
                        print(f"Eval error ({err.__class__.__name__}): {err}")
                    RedPrint("Invalid float value.", exit_after=False)
                    continue
                if not isinstance(evq, float):
                    RedPrint("Invalid float value.", exit_after=False)
                    continue
                with open(file_name, "w") as file:
                    file.write(str(evq))
                break
        elif file_type not in ["Folder", "Class", "ValueArray", "Workspace"]:
            Run(file_name, highlights)
        else:
            with open(file_name, "w") as file:
                file.write("")
    else:
        with open(file_name, "w") as file:
            file.write("")
def Interruptible(func, default = None) -> Callable:
    def Wrapper(*args, **kwargs) -> Any:
        try:
            func(*args, **kwargs)
        except (KeyboardInterrupt, EOFError):
            RedPrint(f"\nOperation cancelled.", exit_after=False)
            return default
    return Wrapper
def InterruptibleDecorator(default = None) -> Callable:
    return lambda func: Interruptible(func, default=default)