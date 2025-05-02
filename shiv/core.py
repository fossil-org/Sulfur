import os, shutil, random
from importlib import import_module
from typing import Any, Callable
from pathlib import Path
from sys import argv, executable
from importlib.util import module_from_spec, spec_from_file_location
from importlib.machinery import SourceFileLoader
from random import randint

from .util import RedPrint, GreenPrint, RunShivim, GetRandomColor, GetCharVariant, select

if os.name == "posix":
    import readline

controls_distance: int = 100
controls_distance_message_shown: bool = False

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
    def GetStringContent(self) -> str:
        if self.__type in ["Folder", "ValueList", "WorkspaceRoot", "Comment"]:
            RedPrint(f"Cannot get string content of a {self.__type}.")
        return self.__content
    def GetContent(self) -> Any:
        if self.__type in ["Folder", "ValueList", "WorkspaceRoot", "Comment"]:
            RedPrint(f"Cannot get content of a {self.__type}.")
        elif self.__type == "ScriptEval":
            return self._Execute(eval)
        elif self.__type == "Integer":
            return int(self.__content)
        elif self.__type == "Boolean":
            return bool(self.__content)
    def _ValueListCheck(self, name: str) -> None:
        if self.__type != "ValueList":
            RedPrint(f"The {name} method is only available for objects of type ValueList.")
    def GetValues(self) -> list[str]:
        self._ValueListCheck("GetValues")
        return [VirtualFile(c).GetStringContent() for c in self.GetChildren()]
    def GetValue(self, i: int) -> str:
        self._ValueListCheck("GetValue")
        if self.GetChild(str(i)) is None:
            RedPrint(f"Could not get value at {i}")
        return self.GetChild(str(i)).GetStringContent()
    def GetRandomValue(self) -> str:
        self._ValueListCheck("GetRandomValue")
        if not self.GetChildren():
            RedPrint(f"No values in {self.__name} to pick from.")
        return self.GetValue(randint(0, len(self.GetChildren()) - 1))
    def _Require(self):
        if self.__type != "ScriptModule":
            RedPrint("Only objects of type ScriptModule can be required in a script.")
        content_path: str = os.path.join(self.__path, "__Content__")
        exec(f"""
class _temp_created_cls:
{'\n'.join(['    '+ln for ln in self.GetStringContent()])}
""".strip(), {
            "shiv": import_module(".", __package__),
            "this": GetVF(os.path.join(self.__path, "__Content__")),
            "require": Require
        })
        return _temp_created_cls
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
        elif self.__type == "Value" and len(self.__content) <= controls_distance / 5 and len(self.__content) != 0:
            return f"\033[94m{self.__name}:\033[0m {self.__content.replace('true', '\033[1;33mtrue\033[0m').replace('false', '\033[1;33mfalse\033[0m')}"
        elif self.__type == "Value":
            return f"\033[94m{self.__name}\033[0m"
        elif self.__type in ["String", "Integer", "Boolean", "Float"] and len(self.__content) <= controls_distance / 5 and len(self.__content) != 0:
            return f"\033[92m{self.__type}\033[0m \033[94m{self.__name}:\033[0m {self.__content.replace('true', '\033[1;33mtrue\033[0m').replace('false', '\033[1;33mfalse\033[0m')}"
        return f"\033[92m{self.__type or 'UnknownType'}\033[0m \033[94m{self.__name}\033[0m"

class FileTreeCLUI:
    def __init__(self, root_path: str):
        self.root = VirtualFile(root_path)
    def InitRoot(self) -> None:
        with open(os.path.join(self.root.GetPath(), "__Content__"), "w") as file:
            file.write("".strip())
        with open(os.path.join(self.root.GetPath(), "__Type__"), "w") as file:
            file.write(f"WorkspaceRoot")
        self.root._LoadMetadata() # NOQA
    def Display(self, node: VirtualFile | None = None, indent: int = 0, order: int = 0, commands: dict[str, Any] | None = None, viewer_mode: bool = False) -> (int, dict[str, Any]):
        global controls_distance, controls_distance_message_shown
        if "-d" in argv:
            i: int = argv.index("-d")
            try:
                ncd: str = argv[i + 1]
            except IndexError:
                RedPrint("-d option requires an argument.", exit_after=False)
                exit(1)
            else:
                ncd = "60" if ncd == "classic" else ncd
                ncd = "100" if ncd == "normal" else ncd
                if not ncd.isdigit():
                    RedPrint("-d option argument must be a digit", exit_after=False)
                    exit(1)
                controls_distance = int(ncd)
                if (controls_distance < 50 or controls_distance > 150) and not controls_distance_message_shown:
                    RedPrint(f"WARNING! -d number under 50 or over 200 can make the text unreadable! 60-125 is recommended.", exit_after=False)
                if not controls_distance_message_shown:
                    RedPrint(f"Set -d number to {controls_distance}", exit_after=False)
                    controls_distance_message_shown = True
        node = node or self.root
        order_char: str = GetCharVariant(order)
        bleed: int = -9 if node.GetType() in ["Value", "Comment"] else 0
        bleed = (11 if "true" in node.GetStringContent() or "false" in node.GetStringContent() else bleed) if node.GetType() not in ["Folder", "ValueList", "WorkspaceRoot", "Comment"] else bleed
        print("  " * indent + str(node), GetRandomColor("-" * (controls_distance - indent * 2 - len(str(node)) + bleed)),
              f" execute: [.{order_char}]" if node.GetType() in ["Script", "ScriptModule", "ScriptEval"] and not viewer_mode else f"\033[90m execute: \033[9m[.{order_char}]\033[0m",
              f" view/edit: [e{order_char}]" if node.GetType() not in ["Folder", "ValueList", "WorkspaceRoot"] and not viewer_mode else f"\033[90m view/edit: \033[9m[e{order_char}]\033[0m",
              f" delete: [d{order_char}]" if indent != 0 and not viewer_mode else f"\033[90m delete: \033[9m[d{order_char}]\033[0m",
              f" rename: [r{order_char}]" if indent != 0 and node.GetType() not in ["Value", "Comment"] and not viewer_mode else f"\033[90m rename: \033[9m[r{order_char}]\033[0m")
        commands = (commands or {}) | {
            "q": exit,
            "c": lambda: (os.system("clear"), self.Display(viewer_mode=viewer_mode), exit()),
            "re": lambda: (GreenPrint("SHIV refreshed!"), self.Display(viewer_mode=viewer_mode), exit())
        }
        if not viewer_mode:
            if node.GetType() not in ["Folder", "ValueList", "WorkspaceRoot"]:
                commands[f"e{order_char}"] = lambda: (RunShivim(os.path.join(node.GetPath(), "__Content__")), GreenPrint("Modification Commited."), self.Display(viewer_mode=viewer_mode), exit())
            else:
                commands[f"e{order_char}"] = lambda: RedPrint(f"Objects of type {node.GetType()} cannot be viewed/edited.")
            if node.GetType() in ["Script", "ScriptEval"]:
                commands[f".{order_char}"] = lambda: (print("\n\n"), node._Execute({ # NOQA
                    "Script": exec,
                    "ScriptEval": lambda *_, **__: print(node._Execute(eval)) # NOQA
                }[node.GetType()]), print("\n\n"), self.Display(viewer_mode=viewer_mode), exit())
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
                new_order, new_commands = self.Display(child, indent + 1, order + 1, commands, viewer_mode=viewer_mode)
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
            f" comment: [c{add_order_char}]" if not viewer_mode else f"\033[90m comment: \033[9m[c{add_order_char}]\033[0m",
            (f" add child: [a{add_order_char}]" if node.GetType() not in ["Value", "Comment"] and not viewer_mode else f"\033[90m add child: \033[9m[a{add_order_char}]\033[0m") if not value_list else f" add value: [a{add_order_char}]" if not viewer_mode else f"\033[90m add value: \033[9m[a{add_order_char}]\033[0m"
        )
        if not viewer_mode:
            if node.GetType() not in ["Value", "Comment"]:
                commands[f"a{add_order_char}"] = lambda: (
                    RunShivim(
                        os.path.join(
                            self.AddChild(
                                node,
                                str(len(node.GetChildren())) if value_list else input("\033[91mChild Name: \033[0m"),
                                "Value" if value_list else select(
                                    "Child type:",
                                    [
                                        "Script",
                                        "ScriptModule",
                                        "ScriptEval",
                                        "Folder",
                                        "ValueList",
                                        "Boolean",
                                        "Integer",
                                        "Float",
                                        "String",
                                    ]
                                ).ask(),
                                ""
                            ),
                            "__Content__")
                    ),
                    GreenPrint(f"Successfully created {'value' if value_list else 'object'}."),
                    self.Display(viewer_mode=viewer_mode),
                    exit()
                )
            else:
                commands[f"a{add_order_char}"] = lambda: RedPrint(f"{node.GetType()}s can only have children of type Comment.")
            commands[f"c{add_order_char}"] = lambda: (self.AddChild(node, f"Comment{add_order}", "Comment", input("\033[90m# ")), print("\033[0m"), GreenPrint(f"Successfully created comment."), self.Display(viewer_mode=viewer_mode), exit())
        if not indent:
            try:
                while True:
                    q: str = input("[cmd] ")

                    if q.startswith("nh"):
                        if viewer_mode:
                            RedPrint("Cannot relaunch shiv in -n (no permissions) mode. Use [re] to reload instead.")
                        GreenPrint("Relaunching shiv here...")
                        os.system(f"{executable} -m shiv {node.GetPath()} {q.removeprefix('nh')}")
                        exit()
                    elif q.startswith("n"):
                        if viewer_mode:
                            RedPrint("Cannot relaunch shiv in -n (no permissions) mode. Use [re] to reload instead.")
                        GreenPrint("Relaunching shiv...")
                        os.system(f"{executable} -m shiv {q.removeprefix('n')}")
                        exit()
                    elif q.startswith("solo"):
                        if viewer_mode:
                            RedPrint("solo for SHIV not available. reason: '-n (no permissions) mode active in this session'", exit_after=False)
                            continue
                        if q.strip() == "solo":
                            GreenPrint("solo for SHIV available.")
                            continue
                        os.system(q.removeprefix("solo"))
                    elif q in ["reset", "reset+q"]:
                        RedPrint(f"/!\\ Are you sure you want to delete ALL objects in \033[3m{node.GetPath()}\033[0m", exit_after=False)
                        try:
                            while True:
                                q2: str = input(f"Type the following to confirm: \033[3m{node.GetName()}\033[0m > ")
                                if q2 == node.GetName():
                                    os.remove(os.path.join(node.GetPath(), "__Content__"))
                                    os.remove(os.path.join(node.GetPath(), "__Type__"))
                                    shutil.rmtree(os.path.join(node.GetPath(), "__Children__"))
                                    if q == "reset+q":
                                        GreenPrint("Reset completed. Exiting SHIV...")
                                        exit()
                                    GreenPrint("Reset completed. Restarting SHIV...")
                                    os.system(f"{executable} -m shiv {node.GetPath()}")
                                    exit()
                                else:
                                    raise KeyboardInterrupt
                        except (KeyboardInterrupt, EOFError):
                            RedPrint("Operation cancelled.", exit_after=False)

                    elif commands.get(q) is not None:
                        commands[q]()
                    elif not q:
                        ...
                    elif viewer_mode:
                        RedPrint(f"\033[91mUnknown command or insufficient permissions to run: [{q}]\033[0m")
                    else:
                        RedPrint(f"\033[91mUnknown command: [{q}]\033[0m")
            except (KeyboardInterrupt, EOFError):
                ...
        return order, commands
    @staticmethod
    def AddChild(parent: VirtualFile, name: str, file_type: str, content: str):
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
    @staticmethod
    def DeleteChild(parent: VirtualFile, name: str):
        child_dir = parent.GetChild(name).GetPath()
        if not os.path.exists(child_dir):
            RedPrint(f"No such object: {name} at {child_dir}")
        shutil.rmtree(child_dir)
    @staticmethod
    def RenameChild(parent: VirtualFile, name: str, new_name: str):
        child_dir = parent.GetChild(name).GetPath()
        if not os.path.exists(child_dir):
            RedPrint(f"No such object: {name} at {child_dir}")
        new_name = new_name.strip("/\\ \t")
        new_name = new_name if new_name and "/" not in new_name and "\\" not in new_name else parent.GetChild(name).GetType()
        os.rename(child_dir, os.path.join(child_dir, "..", new_name))