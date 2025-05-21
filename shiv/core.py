"""
SHIV windows/linux release
source: https://github.com/fossil-org/SHIV

Developed by: pilot (gh: pilot-gh)
Published by: FOSSIL (gh: fossil-org)

Est.
2025
"""

import os, shutil, random, webbrowser, sys
from importlib import import_module
from typing import Any, Callable
from pathlib import Path
from sys import argv, executable
from importlib.util import module_from_spec, spec_from_file_location
from importlib.machinery import SourceFileLoader
from random import randint
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

from .util import RedPrint, GreenPrint, RunShivim, GetRandomColor, GetCharVariant, OBJECT_TYPE_LIST, GetHighlight, ANSI_COLORS

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
        if self.__type in ["Folder", "Class", "ValueList", "Workspace", "Comment"]:
            RedPrint(f"Cannot get string content of a {self.__type}.")
        return self.__content
    def GetContent(self) -> Any:
        if self.__type in ["Folder", "ValueList", "Workspace", "Comment"]:
            RedPrint(f"Cannot get content of a {self.__type}.")
        elif self.__type == "ScriptEval":
            return self._Execute(eval)
        elif self.__type == "WholeNumber":
            return int(self.__content)
        elif self.__type == "State":
            return eval(self.__content.capitalize())
        elif self.__type == "Class":
            return self._Class()
        elif self.__type == "Color":
            return self.__content.split("#")[1]
        else:
            return self.__content
    def Open(self) -> None:
        if self.__type == "URL":
            webbrowser.open(self.__content)
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
    def _Class(self):
        if self.__type != "Class":
            RedPrint("Only objects of type Class can be interpreted as a class in a script.")
        attributes: dict[str, Any] = {}
        for child in [VirtualFile(p) for p in self.GetChildren()]:
            if child.GetType() == "Comment":
                continue
            attributes |= {child.GetName(): {
                "Class": lambda p: VirtualFile(p).Class(),
                "ValueList": lambda p: VirtualFile(p).GetValues(),
                "State": lambda p: VirtualFile(p).GetContent(),
                "WholeNumber": lambda p: VirtualFile(p).GetContent(),
                "DecimalNumber": lambda p: VirtualFile(p).GetContent(),
                "Text": lambda p: VirtualFile(p).GetContent()
            }.get(child.GetType(), VirtualFile)(child.GetPath())}
        return type(self.GetName(), (), attributes)()
    def _Require(self):
        from . import GetVF, Require
        if self.__type != "ScriptModule":
            RedPrint("Only objects of type ScriptModule can be required in a script.")
        module_vars: dict[str, Any] = {
            "this": GetVF(os.path.join(self.__path, "__Content__")),
            "require": Require
        }
        exec(f"""
class _temp_created_cls:
{'\n'.join(['    '+ln for ln in self.GetStringContent().split('\n')])}
""".strip(), module_vars)
        return module_vars["_temp_created_cls"]
    def _Execute(self, protocol: Callable) -> None:
        from . import GetVF, Require
        return protocol(self.__content, {
            "this": GetVF(os.path.join(self.__path, "__Content__")),
            "require": Require
        })
    def __str__(self):
        if self.__type == "Comment":
            return f"\033[90m# {self.__content}\033[0m"
        elif self.__type == "Value" and len(self.__content) <= controls_distance / 5 and len(self.__content) != 0:
            return f"\033[94m{self.__name}:\033[0m {self.__content.replace('\n', ' ').replace('true', '\033[1;33mtrue\033[0m').replace('false', '\033[1;33mfalse\033[0m')}"
        elif self.__type == "Value":
            return f"\033[94m{self.__name}\033[0m"
        elif self.__type in ["Text", "WholeNumber", "State", "DecimalNumber", "Character", "URL"] and len(self.__content) <= controls_distance / 5 and len(self.__content) != 0:
            return f"\033[92m{self.__type}\033[0m \033[94m{self.__name}:\033[0m {self.__content.replace('\n', ' ').replace('true', '\033[1;33mtrue\033[0m').replace('false', '\033[1;33mfalse\033[0m')}"
        elif self.__type == "Color":
            color: str = self.__content.split("#")[0]
            return f"\033[92m{self.__type}\033[0m \033[94m{self.__name}:\033[0m {ANSI_COLORS[int(color)] if color.isdigit() else color}"
        return f"\033[92m{self.__type or 'UnknownType'}\033[0m \033[94m{self.__name}\033[0m"

class FileTreeCLUI:
    def __init__(self, root_path: str):
        self.root = VirtualFile(root_path)
    def InitRoot(self) -> None:
        with open(os.path.join(self.root.GetPath(), "__Content__"), "w") as file:
            file.write("".strip())
        with open(os.path.join(self.root.GetPath(), "__Type__"), "w") as file:
            file.write(f"Workspace")
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
        bleed = (11 if "true" in node.GetStringContent() or "false" in node.GetStringContent() else bleed) if node.GetType() not in ["Folder", "Class", "ValueList", "Workspace", "Comment"] else bleed
        print("  " * indent + str(node), GetRandomColor("-" * (controls_distance - indent * 2 - len(str(node)) + bleed)),
              f" {'example' if node.GetType() == 'Color' else ('browser' if node.GetType() == 'URL' else 'execute')}: [.{order_char}]" if node.GetType() in ["Script", "ScriptEval", "ShellScript", "Color", "URL", "MavroScript"] and not viewer_mode else f"\033[90m {'example' if node.GetType() == 'Color' else ('browser' if node.GetType() == 'URL' else 'execute')}: \033[9m[.{order_char}]\033[0m",
              f" view/edit: [e{order_char}]" if node.GetType() not in ["Folder", "Class", "ValueList", "Workspace"] and not viewer_mode else f"\033[90m view/edit: \033[9m[e{order_char}]\033[0m",
              f" delete: [d{order_char}]" if indent != 0 and not viewer_mode else f"\033[90m delete: \033[9m[d{order_char}]\033[0m",
              f" rename: [r{order_char}]" if indent != 0 and node.GetType() not in ["Value", "Comment"] and not viewer_mode else f"\033[90m rename: \033[9m[r{order_char}]\033[0m")
        commands = (commands or {}) | {
            "q": exit,
            "c": lambda: (os.system("clear"), self.Display(viewer_mode=viewer_mode), exit()),
            "re": lambda: (GreenPrint("SHIV refreshed!"), self.Display(viewer_mode=viewer_mode), exit())
        }
        if not viewer_mode:
            if node.GetType() not in ["Folder", "Class", "ValueList", "Workspace"]:
                commands[f"e{order_char}"] = lambda: (RunShivim(os.path.join(node.GetPath(), "__Content__"), GetHighlight(node.GetType())), GreenPrint("Modification Commited."), self.Display(viewer_mode=viewer_mode), exit())
            else:
                commands[f"e{order_char}"] = lambda: RedPrint(f"Objects of type {node.GetType()} cannot be viewed/edited.")
            if node.GetType() in ["Script", "ScriptEval", "ShellScript", "MavroScript"]:
                commands[f".{order_char}"] = lambda: (print("\n\n"), node._Execute({ # NOQA
                    "Script": exec,
                    "ScriptEval": lambda *_, **__: print(node._Execute(eval)), # NOQA
                    "ShellScript": lambda *_, **__: os.system(node.GetContent()),
                    "MavroScript": lambda *_, **__: os.system(f"{sys.executable} -m msq {os.path.join(node.GetPath(), '__Content__')}")
                }[node.GetType()]), print("\n\n"), self.Display(viewer_mode=viewer_mode), exit())
            elif node.GetType() == "Color":
                commands[f".{order_char}"] = lambda: print(f"\n\n{node.GetStringContent().split('#')[1]}{node.GetName()}: {node.GetStringContent().split('#')[0]}\n\nHello, world!\033[0m\n\n")
            elif node.GetType() == "URL":
                commands[f".{order_char}"] = lambda: webbrowser.open(node.GetContent())
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
            f" add {'value' if value_list else 'child'}: [a{add_order_char}]" if not viewer_mode and node.GetType() not in ["Value", "Comment"] else f"\033[90m add {'value' if value_list else 'child'}: \033[9m[a{add_order_char}]\033[0m"
        )
        obj_type: str = ""
        def GetObjectType(new: bool = True) -> str:
            nonlocal obj_type
            if not new:
                return obj_type
            while True:
                RedPrint("Child Type:", exit_after=False)
                q3: str = prompt(
                    "- ",
                    completer=WordCompleter(OBJECT_TYPE_LIST, ignore_case=True)
                )
                if q3 not in OBJECT_TYPE_LIST:
                    RedPrint(f"Invalid object type: {q3}", exit_after=False)
                    RedPrint(f"Run [h] for a list of object types.", exit_after=False)
                    continue
                obj_type = q3
                return q3
        if not viewer_mode:
            if node.GetType() not in ["Value", "Comment"]:
                commands[f"a{add_order_char}"] = lambda: (
                    RunShivim(
                        os.path.join(
                            self.AddChild(
                                node,
                                str(len(node.GetChildren())) if value_list else input("\033[91mChild Name: \033[0m"),
                                "Value" if value_list else GetObjectType(),
                                ""
                            ),
                            "__Content__"
                        ),
                        GetHighlight(GetObjectType(new=False))
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
                    if q == "h":
                        print("List of object types:")
                        for t in OBJECT_TYPE_LIST:
                            print(f"- {GetRandomColor(t, force=True)}")
                    elif q == "hc":
                        GreenPrint("Hint: run [n -c] or [nh -c] or start shiv with the -c option (shiv (...) -c) to enter color mode where some items are easier to tell apart.")
                        print(*[GetRandomColor(p) for p in "This line will appear colorful in color mode. Try it yourself!".split(" ")])
                        print("\nList of colors (for Color object):")
                        print(*[f"{k}: {v}" for k, v in ANSI_COLORS.keys()], "24-bit colors are also supported.", sep="\n")
                    elif q in ["au", "cr"]:
                        GreenPrint(__doc__)
                    elif viewer_mode:
                        RedPrint(f"\033[91mUnknown command or insufficient permissions to run: [{q}]\033[0m")
                    elif q.startswith("nh"):
                        GreenPrint("Relaunching shiv here...")
                        os.system(f"{executable} -m shiv {node.GetPath()} {q.removeprefix('nh')}")
                        exit()
                    elif q.startswith("n"):
                        GreenPrint("Relaunching shiv...")
                        os.system(f"{executable} -m shiv {q.removeprefix('n')}")
                        exit()
                    elif q == "xp":
                        GreenPrint("Export process started.")
                        def Iterate(p: str) -> None:
                            for f in VirtualFile(p).GetChildren():
                                f = VirtualFile(f)
                                if f.GetType() == "Comment":
                                    continue
                                GreenPrint(f"Exporting: {f.GetPath()}")
                                shutil.copy(os.path.join(f.GetPath(), "__Content__"), os.path.join(f"{node.GetName()}.export", f"{f.GetName()}.{f.GetType().lower()}"))
                                Iterate(f.GetPath())
                        if os.path.exists(f"{node.GetName()}.export"):
                            RedPrint(f"{node.GetName()}.export already exists! Delete it with the [rmxp] command or move it manually first before making a new export.")
                        os.mkdir(f"{node.GetName()}.export")
                        Iterate(node.GetPath())
                        GreenPrint(f"Export completed! See results in {node.GetName()}.export")
                    elif q == "rmxp":
                        if os.path.exists(f"{node.GetName()}.export"):
                            shutil.rmtree(f"{node.GetName()}.export")
                            GreenPrint("Current export deleted.")
                        else:
                            RedPrint("No export to delete!")
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