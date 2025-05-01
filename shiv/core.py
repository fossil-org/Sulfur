import os, json, shutil, random
from importlib import import_module
from typing import Any, Callable
from pathlib import Path
from sys import argv, executable
from importlib.util import module_from_spec, spec_from_file_location
from importlib.machinery import SourceFileLoader
from random import randint

from .shivim import run

controls_distance: int = 60
controls_distance_message_shown: bool = False

def RedPrint(*s: str, sep: str = " ", exit_after: bool = True) -> None:
    if exit_after:
        raise Exception(f"\033[91m{sep.join(s)}\033[0m")
    else:
        print(f"\033[91m{sep.join(s)}\033[0m")

try:
    from questionary import select
except ModuleNotFoundError:
    RedPrint("Unfulfilled dependency: questionary", exit_after=False)
    exit(1)
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

class VirtualFile:
    def __init__(self, path: str):
        self.__path: str = os.path.abspath(path)
        self.__name: str = os.path.basename(path)
        self.__type: str | None = None
        self.__content: str | None = None
        self._LoadMetadata()

    def _LoadMetadata(self):
        try:
            with open(os.path.join(self.__path, "__Type__")) as file:
                self.__type = file.read().strip()
            with open(os.path.join(self.__path, "__Content__")) as file:
                self.__content = file.read()
            os.makedirs(os.path.join(self.__path, "__Children__"), exist_ok=True)
        except FileNotFoundError:
            self.__type = None
            self.__content = None
    def GetChild(self, name: str) -> "VirtualFile | None":
        child_path = os.path.join(self.__path, "__Children__", name)
        if os.path.isdir(child_path):
            return VirtualFile(child_path)
        return None
    def GetChildren(self) -> list[str]:
        children_dir = os.path.join(self.__path, "__Children__")
        return [str(s) for s in sorted(Path(os.path.join(self.__path, "__Children__")).iterdir(), key=lambda f: f.stat().st_ctime)]
    def GetParent(self) -> "VirtualFile | None":
        if os.path.basename(os.path.abspath(os.path.join(self.__path, ".."))) == "__Children__":
            return VirtualFile(os.path.join(self.__path, "..", ".."))
        return None
    def GetSibling(self, name: str) -> "VirtualFile | None":
        parent: VirtualFile = self.GetParent()
        if parent:
            return parent.GetChild(name)
        return None
    def GetPath(self) -> str:
        return self.__path
    def GetName(self) -> str:
        return self.__name
    def GetType(self) -> str:
        return self.__type
    def GetContent(self) -> str:
        if self.__type == "Comment":
            RedPrint("Cannot get content of a comment.")
        return self._Execute(eval) if self.__type == "ScriptEval" else self.__content
    def _ValueListCheck(self, name: str) -> None:
        if self.__type != "ValueList":
            RedPrint(f"The {name} method is only available for objects of type ValueList.")
    def GetValues(self) -> list[str]:
        self._ValueListCheck("GetValues")
        return [c.GetContent() for c in self.GetChildren()]
    def GetValue(self, i: int) -> str:
        self._ValueListCheck("GetValue")
        if self.GetChild(str(i)) is None:
            RedPrint(f"Could not get value at {i}")
        return self.GetChild(str(i)).GetContent()
    def GetRandomValue(self) -> str:
        self._ValueListCheck("GetRandomValue")
        if not self.GetChildren():
            RedPrint(f"No values in {self.__name} to pick from.")
        return self.GetValue(randint(0, len(self.GetChildren()) - 1))
    def Require(self):
        if self.__type != "ScriptModule":
            RedPrint("Only objects of type ScriptModule can be required in a script.")
        content_path: str = os.path.join(self.__path, "__Content__")
        loader = SourceFileLoader(self.__name, content_path)
        spec = spec_from_file_location(self.__name, content_path, loader=loader)
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    def _Execute(self, protocol: Callable) -> None:
        from . import GetVF, Require
        return protocol(self.__content, {
            "shiv": import_module(".", __package__),
            "this": GetVF(os.path.join(self.__path, "__Content__")),
            "require": Require
        })
    def __str__(self):
        if self.__type == "Comment":
            return f"\033[90m# {self.__content}\033[0m"
        elif self.__type == "Value" and len(self.__content) <= controls_distance / 10:
            return f"\033[94m{self.__name}:\033[0m {self.__content}"
        elif self.__type == "Value" and len(self.__content) > controls_distance / 10:
            return f"\033[94m{self.__name}\033[0m"
        return f"\033[92m{self.__type or "UnknownType"}\033[0m \033[94m{self.__name}\033[0m"

class FileTreeCLUI:
    def __init__(self, root_path: str):
        self.root = VirtualFile(root_path)
    def InitRoot(self) -> None:
        with open(os.path.join(self.root.GetPath(), "__Content__"), "w") as file:
            file.write(
f"""
This is the WorkspaceRoot object of the SHIV environment at {os.path.abspath(self.root.GetPath())}.

Learn more about SHIV here: https://github.com/fossil-org/SHIV.

External changes made to this file will be reset when the SHIV CLI is exited.
""".strip())
        with open(os.path.join(self.root.GetPath(), "__Type__"), "w") as file:
            file.write(f"WorkspaceRoot")
        self.root._LoadMetadata()
    def Display(self, node: VirtualFile | None = None, indent: int = 0, order: int = 0, commands: dict[str, Any] | None = None) -> (int, dict[str, Any]):
        global controls_distance, controls_distance_message_shown
        if "-d" in argv:
            i: int = argv.index("-d")
            try:
                ncd: str = argv[i + 1]
            except IndexError:
                RedPrint("-d option requires an argument.", exit_after=False)
                exit(1)
            else: # using else to bypass ide's thinking ncd could be undefined
                ncd = "60" if ncd == "classic" else ncd
                ncd = "100" if ncd == "extended" else ncd
                if not ncd.isdigit():
                    RedPrint("-d option argument must be a digit", exit_after=False)
                    exit(1)
                controls_distance = int(ncd)
                if (controls_distance < 50 or controls_distance > 150) and not controls_distance_message_shown:
                    RedPrint(f"WARNING! -d number under 50 or over 150 can make the text unreadable! -d 60 or -d 100 is recommended.", exit_after=False)
                if not controls_distance_message_shown:
                    RedPrint(f"Set -d number to {controls_distance}", exit_after=False)
                    controls_distance_message_shown = True
        node = node or self.root
        order_char: str = GetCharVariant(order)
        bleed: int = -9 if node.GetType() == "Value" and len(node.GetContent()) <= controls_distance / 10 else 0
        bleed      = -9 if node.GetType() in ["Value", "Comment"] else bleed
        print("  " * indent + str(node), GetRandomColor("-" * (controls_distance - indent * 2 - len(str(node)) + bleed)),
              f" execute: [.{order_char}]" if node.GetType() in ["Script", "ScriptModule", "ScriptEval"] else f"\033[90m execute: \033[9m[.{order_char}]\033[0m",
              f" view/edit: [e{order_char}]" if node.GetType() not in ["Folder", "ValueList", "WorkspaceRoot"] else f"\033[90m view/edit: \033[9m[e{order_char}]\033[0m",
              f" delete: [d{order_char}]" if indent != 0 else f"\033[90m delete: \033[9m[d{order_char}]\033[0m",
              f" rename: [r{order_char}]" if indent != 0 and node.GetType() not in ["Value", "Comment"] else f"\033[90m rename: \033[9m[r{order_char}]\033[0m")
        commands = (commands or {}) | {
            "q": exit,
            "c": lambda: (os.system("clear"), self.Display(), exit()),
            "re": lambda: (GreenPrint("SHIV refreshed!"), self.Display(), exit())
        }
        if node.GetType() not in ["Folder", "ValueList", "WorkspaceRoot"]:
            commands[f"e{order_char}"] = lambda: (run(os.path.join(node.GetPath(), "__Content__")), GreenPrint("Modification Commited."), self.Display(), exit())
        else:
            commands[f"e{order_char}"] = lambda: RedPrint(f"Objects of type {node.GetType()} cannot be viewed/edited.")
        if node.GetType() in ["Script", "ScriptEval"]:
            commands[f".{order_char}"] = lambda: (print("\n\n"), node._Execute({
                "Script": exec,
                "ScriptEval": lambda *_, **__: print(node._Execute(eval))
            }[node.GetType()]), print("\n\n"), self.Display(), exit())
        else:
            commands[f".{order_char}"] = lambda: RedPrint(f"Objects of type {node.GetType()} cannot be executed.")
        if indent != 0 and node.GetType() not in ["Value", "Comment"]:
            commands[f"r{order_char}"] = lambda: (self.RenameChild(VirtualFile(os.path.join(node.GetPath(), "..", "..")), node.GetName(), input("\033[91mNew Name: \033[0m")), GreenPrint("Successfully renamed object."), self.Display(), exit())
        else:
            commands[f"r{order_char}"] = lambda: RedPrint(f"Objects of type {node.GetType()} cannot be renamed.")
        if indent != 0:
            commands[f"d{order_char}"] = lambda: (self.DeleteChild(VirtualFile(os.path.join(node.GetPath(), "..", "..")), node.GetName()), GreenPrint("Successfully removed object."), self.Display(), exit())
        else:
            commands[f"d{order_char}"] = lambda: RedPrint(f"Objects of type {node.GetType()} cannot be deleted.")
        for child_name in node.GetChildren():
            child = node.GetChild(child_name)
            if child:
                new_order, new_commands = self.Display(child, indent + 1, order + 1, commands)
                order = new_order
                commands = new_commands
        add_order: int = 0
        while True:
            if f"a{GetCharVariant(add_order)}" in commands.keys():
                add_order += 1
                continue
            break
        add_order_char: str = GetCharVariant(add_order)
        value_list: bool = node.GetType() == "ValueList"
        print("  " * indent + "\033[90m  ...\033[0m", ("\033[90m-\033[0m" * (controls_distance - indent * 2 - 20 - 3)),
              f" comment: [c{add_order_char}]",
              (f" add child: [a{add_order_char}]" if node.GetType() not in ["Value", "Comment"] else f"\033[90m add child: \033[9m[a{add_order_char}]\033[0m") if not value_list else f" add value: [a{add_order_char}]"
              )
        if node.GetType() not in ["Value", "Comment"]:
            commands[f"a{add_order_char}"] = lambda: (
                run(
                    os.path.join(
                        self.AddChild(
                            node,
                            str(len(node.GetChildren())) if value_list else input("\033[91mChild Name: \033[0m"),
                            "Value" if value_list else select(
                                "Child Type:",
                                [
                                    "Script",
                                    "ScriptModule",
                                    "ScriptEval",
                                    "Folder",
                                    "ValueList",
                                    "String",
                                ]
                            ).ask(),
                            ""
                        ),
                        "__Content__")
                ),
                GreenPrint(f"Successfully created {'value' if value_list else 'object'}."),
                self.Display(),
                exit()
            )
        else:
            commands[f"a{add_order_char}"] = lambda: RedPrint(f"{node.GetType()}s can only have children of type Comment.")
        commands[f"c{add_order_char}"] = lambda: (self.AddChild(node, f"Comment{add_order}", "Comment", input("\033[90m# ")), print("\033[0m"), GreenPrint(f"Successfully created comment."), self.Display(), exit())
        if not indent:
            try:
                while True:
                    q: str = input("[cmd] ")

                    if q.startswith("nh"):
                        GreenPrint("Relaunching shiv here...")
                        os.system(f"{executable} -m shiv {node.GetPath()} {q.removeprefix('nh')}")
                        exit()
                    elif q.startswith("n"):
                        GreenPrint("Relaunching shiv...")
                        os.system(f"{executable} -m shiv {q.removeprefix('n')}")
                        exit()
                    elif commands.get(q) is not None:
                        commands[q]()
                    elif not q:
                        ...
                    else:
                        RedPrint(f"\033[91mUnknown command: [{q}]\033[0m")
            except (KeyboardInterrupt, EOFError):
                ...
        return order, commands
    def AddChild(self, parent: VirtualFile, name: str, file_type: str, content: str):
        name = name.strip("/\\ \t")
        name = name if name and "/" not in name and "\\" not in name else file_type
        child_dir = os.path.join(parent.GetPath(), "__Children__", name)
        if os.path.exists(child_dir):
            RedPrint(f"Object of name '{name}' already exists in that location! Delete it first if you want to overwrite it.")
        os.makedirs(child_dir)
        with open(os.path.join(child_dir, "__Type__"), 'w') as f:
            f.write(file_type)
        with open(os.path.join(child_dir, "__Content__"), 'w') as f:
            f.write(content)
        os.makedirs(os.path.join(child_dir, "__Children__"))
        return child_dir
    def DeleteChild(self, parent: VirtualFile, name: str):
        child_dir = parent.GetChild(name).GetPath()
        if not os.path.exists(child_dir):
            RedPrint(f"No such object: {name} at {child_dir}")
        shutil.rmtree(child_dir)
    def RenameChild(self, parent: VirtualFile, name: str, new_name: str):
        child_dir = parent.GetChild(name).GetPath()
        if not os.path.exists(child_dir):
            RedPrint(f"No such object: {name} at {child_dir}")
        new_name = new_name.strip("/\\ \t")
        new_name = new_name if new_name and "/" not in new_name and "\\" not in new_name else parent.GetChild(name).GetType()
        os.rename(child_dir, os.path.join(child_dir, "..", new_name))