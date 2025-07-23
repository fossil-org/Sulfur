"""
Sulfur windows/linux release
source: https://github.com/fossil-org/Sulfur

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

from .util import RedPrint, GreenPrint, RunEditor, GetRandomColor, GetCharVariant, ForceRemove, OBJECT_TYPE_LIST, GetHighlight, ANSI_COLORS, SEP, Interruptible
from .spm import Plugin, PluginError

if os.name == "posix":
    import readline

controls_distance: int = 100
controls_distance_message_shown: bool = False

global_storage: dict[str, Any] = {}

class File:
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
            return File(child_path)
        return None
    def GetChildren(self) -> list[str]:
        return [str(s) for s in sorted(Path(os.path.join(self.__path, "__Children__")).iterdir(), key=lambda f: f.stat().st_ctime)]
    def GetParent(self) -> "VirtualFile | None":
        if os.path.basename(os.path.abspath(os.path.join(self.__path, ".."))) == "__Children__":
            return File(os.path.join(self.__path, "..", ".."))
        return None
    def GetSibling(self, name: str) -> "VirtualFile | None":
        parent: File = self.GetParent()
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
        if self.__type in ["Folder", "Class", "ValueArray", "Workspace", "Comment"]:
            RedPrint(f"Cannot get string content of a {self.__type}.", exit_after=False)
        return self.__content
    def GetContent(self) -> Any:
        if self.__type in ["Folder", "ValueArray", "Workspace", "Comment"]:
            RedPrint(f"Cannot get content of a {self.__type}.", exit_after=False)
        elif self.__type == "ScriptEval":
            return self._Execute(eval)
        elif self.__type == "Integer":
            return int(self.__content)
        elif self.__type == "Boolean":
            return eval(self.__content.capitalize())
        elif self.__type == "Class":
            return self._Class()
        elif self.__type == "Color":
            return self.__content.split("#")[1]
        else:
            return self.__content
    def Open(self) -> None:
        if self.__type != "URL":
            RedPrint(f"The Open method is only available for objects of type URL.", exit_after=False)
        webbrowser.open(self.__content)
    def _ValueListCheck(self, name: str) -> None:
        if self.__type != "ValueArray":
            RedPrint(f"The {name} method is only available for objects of type ValueArray.", exit_after=False)
    def GetValues(self) -> list[str]:
        self._ValueListCheck("GetValues")
        return [File(c).GetStringContent() for c in self.GetChildren()]
    def GetValue(self, i: int) -> str:
        self._ValueListCheck("GetValue")
        if self.GetChild(str(i)) is None:
            RedPrint(f"Could not get value at {i}", exit_after=False)
        return self.GetChild(str(i)).GetStringContent()
    def GetRandomValue(self) -> str:
        self._ValueListCheck("GetRandomValue")
        if not self.GetChildren():
            RedPrint(f"No values in {self.__name} to pick from.", exit_after=False)
        return self.GetValue(randint(0, len(self.GetChildren()) - 1))
    def _Class(self):
        if self.__type != "Class":
            RedPrint("Only objects of type Class can be interpreted as a class in a script.", exit_after=False)
        attributes: dict[str, Any] = {}
        for child in [File(p) for p in self.GetChildren()]:
            if child.GetType() == "Comment":
                continue
            attributes |= {child.GetName(): {
                "Class": lambda p: File(p).Class(),
                "ValueArray": lambda p: File(p).GetValues(),
                "Boolean": lambda p: File(p).GetContent(),
                "Integer": lambda p: File(p).GetContent(),
                "Double": lambda p: File(p).GetContent(),
                "String": lambda p: File(p).GetContent()
            }.get(child.GetType(), File)(child.GetPath())}
        return type(self.GetName(), (), attributes)()
    def _Require(self):
        from . import GetFile, Require
        if self.__type != "ScriptModule":
            RedPrint("Only objects of type ScriptModule can be required in a script.", exit_after=False)
        module_vars: dict[str, Any] = {
            "this": GetFile(os.path.join(self.__path, "__Content__")),
            "require": Require
        }
        exec(f"""
class _temp_created_cls:
{'\n'.join(['    '+ln for ln in self.GetStringContent().split('\n')])}
""".strip(), module_vars)
        return module_vars["_temp_created_cls"]
    def _Execute(self, protocol: Callable | None = None, force: bool = False) -> None:
        from . import GetFile, Require
        with open(os.path.join(self.__path, "__Type__")) as file:
            content: str = file.read()
        trace: str | None = Plugin.TraceObjectType(content)
        if trace is not None and not force:
            ot_content: dict = Plugin.ReadObjectType(trace)
            ExecString = lambda sl: ("\n".join(sl) if isinstance(sl, list) else sl).replace('\x00', '')
            protocol = lambda s, v: exec(ExecString((ot_content["Execute"] or {}).get("Command") or "print('No command specified for this operation.')"), v | {"global_storage": global_storage})
        return protocol(self.__content, {
            "this": GetFile(os.path.join(self.__path, "__Content__")),
            "require": Require
        })
    def __str__(self):
        t = self.__type
        if ":" in t:
            t = (Plugin.ReadObjectType(Plugin.TraceObjectType(t))["Display"] or {}).get("InheritsFrom") or "UnknownType"
        if t == "Comment":
            return f"\033[90m# {self.__content}\033[0m"
        elif t == "Value" and len(self.__content) <= controls_distance / 5 and len(self.__content) != 0:
            return f"\033[94m{self.__name}:\033[0m {self.__content.replace('\n', ' ').replace('true', '\033[1;33mtrue\033[0m').replace('false', '\033[1;33mfalse\033[0m')}"
        elif t == "Value":
            return f"\033[94m{self.__name}\033[0m"
        elif t in ["String", "Integer", "Boolean", "Double", "Character", "URL"] and len(self.__content) <= controls_distance / 5 and len(self.__content) != 0:
            return f"\033[92m{self.__type}\033[0m \033[94m{self.__name}:\033[0m {self.__content.replace('\n', ' ').replace('true', '\033[1;33mtrue\033[0m').replace('false', '\033[1;33mfalse\033[0m')}"
        elif t == "Color":
            color: str = self.__content.split("#")[0]
            return f"\033[92m{self.__type}\033[0m \033[94m{self.__name}:\033[0m {ANSI_COLORS[int(color)] if color.isdigit() else color}"
        return f"\033[92m{self.__type or 'UnknownType'}\033[0m \033[94m{self.__name}\033[0m"

class FileTreeCLUI:
    def __init__(self, root_path: str):
        self.root = File(root_path)
    def InitRoot(self) -> None:
        with open(os.path.join(self.root.GetPath(), "__Content__"), "w") as file:
            file.write("")
        with open(os.path.join(self.root.GetPath(), "__Type__"), "w") as file:
            file.write(f"Workspace")
        self.root._LoadMetadata() # NOQA
    def Display(self, node: File | None = None, indent: int = 0, order: int = 0, commands: dict[str, Any] | None = None, viewer_mode: bool = False) -> (int, dict[str, Any]):
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
        bleed = (11 if "true" in node.GetStringContent() or "false" in node.GetStringContent() else bleed) if node.GetType() not in ["Folder", "Class", "ValueArray", "Workspace", "Comment"] else bleed
        t, et, ht = [node.GetType()] * 3
        ea = True
        if ":" in t:
            try:
                et = (Plugin.ReadObjectType(Plugin.TraceObjectType(t))["Execute"] or {}).get("InheritsFrom") or t
                ht = (Plugin.ReadObjectType(Plugin.TraceObjectType(t))["Highlights"] or {}).get("InheritsFrom") or "UnknownType"
                ea = (Plugin.ReadObjectType(Plugin.TraceObjectType(t))["Editor"] or {}).get("Enabled", True)
            except AttributeError as err:
                PluginError(err, Plugin.FromPath(str(Path(Plugin.TraceObjectType(t)).parent)))
        print("  " * indent + str(node), GetRandomColor("-" * (controls_distance - indent * 2 - len(str(node)) + bleed)),
              f" {'toggled' if et == "Boolean" else ('example' if et == 'Color' else ('browser' if et == 'URL' else 'execute'))}: [.{order_char}]" if et in (["Script", "ScriptEval", "ShellScript", "Color", "URL", "Boolean"] + Plugin.GetExecutableObjectTypes(Plugin.GetEnabledPlugins())) and not viewer_mode else f"\033[90m {'toggled' if et == 'Boolean' else ('example' if et == 'Color' else ('browser' if et == 'URL' else 'execute'))}: \033[9m[.{order_char}]\033[0m",
              f" view/edit: [e{order_char}]" if node.GetType() not in ["Folder", "Class", "ValueArray", "Workspace"] and not viewer_mode and ea else f"\033[90m view/edit: \033[9m[e{order_char}]\033[0m",
              f" delete: [d{order_char}]" if indent != 0 and not viewer_mode else f"\033[90m delete: \033[9m[d{order_char}]\033[0m",
              f" rename: [r{order_char}]" if indent != 0 and node.GetType() not in ["Value", "Comment"] and not viewer_mode else f"\033[90m rename: \033[9m[r{order_char}]\033[0m")
        commands: dict[str, Any] = (commands or {}) | {
            "q": exit,
            "c": lambda: (os.system("clear"), self.Display(viewer_mode=viewer_mode), exit()),
            "re": lambda: (GreenPrint("Sulfur refreshed!"), self.Display(viewer_mode=viewer_mode), exit())
        }
        if not viewer_mode:
            if ea and t not in ["Folder", "Class", "ValueArray", "Workspace"]:
                commands[f"e{order_char}"] = lambda: (RunEditor(os.path.join(node.GetPath(), "__Content__"), GetHighlight(ht) + ((Plugin.ReadObjectType(Plugin.TraceObjectType(t))["Highlights"] or {}).get("List") or [])), GreenPrint("Modification commited."), self.Display(viewer_mode=viewer_mode), exit())
            else:
                commands[f"e{order_char}"] = lambda: RedPrint(f"Objects of type {t} cannot be viewed/edited.", exit_after=False)
            if et in (["Script", "ScriptEval", "ShellScript"] + Plugin.GetExecutableObjectTypes(Plugin.GetEnabledPlugins())):
                commands[f".{order_char}"] = lambda: (print(), node._Execute({ # NOQA
                    "Script": exec,
                    "ScriptEval": lambda *_, **__: print(node._Execute(eval)), # NOQA
                    "ShellScript": lambda *_, **__: os.system(node.GetContent()),
                }.get(et, None), force=et != t), print(), self.Display(viewer_mode=viewer_mode), exit())
            elif et == "Color":
                commands[f".{order_char}"] = lambda: print(f"\n\n{node.GetStringContent().split('#')[1]}{node.GetName()}: {node.GetStringContent().split('#')[0]}\n\nHello, world!\033[0m\n\n")
            elif et == "Boolean":
                commands[f".{order_char}"] = lambda: (
                    exec("with open(f'{node.GetPath()}{SEP}__Content__', 'w') as file: file.write(str(not node.GetContent()).lower())", {"node": node, "SEP": SEP}),
                    self.Display(viewer_mode=viewer_mode),
                    exit()
                )
            elif et == "URL":
                commands[f".{order_char}"] = lambda: webbrowser.open(node.GetContent())
            else:
                commands[f".{order_char}"] = lambda: RedPrint(f"Objects of type {et} cannot be executed.", exit_after=False)
            if indent != 0 and node.GetType() not in ["Value", "Comment"]:
                commands[f"r{order_char}"] = Interruptible(lambda: (self.RenameChild(File(os.path.join(node.GetPath(), "..", "..")), node.GetName(), input("\033[91mNew Name: \033[0m")), GreenPrint("Successfully renamed object."), self.Display(), exit()))
            else:
                commands[f"r{order_char}"] = lambda: RedPrint(f"Objects of type {node.GetType()} cannot be renamed.", exit_after=False)
            if indent != 0:
                commands[f"d{order_char}"] = lambda: (self.DeleteChild(File(os.path.join(node.GetPath(), "..", "..")), node.GetName()), GreenPrint("Successfully removed object."), self.Display(), exit())
            else:
                commands[f"d{order_char}"] = lambda: RedPrint(f"Objects of type {node.GetType()} cannot be deleted.", exit_after=False)
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
        value_list: bool = node.GetType() == "ValueArray"
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
                commands[f"a{add_order_char}"] = Interruptible(lambda: (
                    RunEditor(
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
                ))
            else:
                commands[f"a{add_order_char}"] = lambda: RedPrint(f"{node.GetType()}s can only have children of type Comment.", exit_after=False)
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
                        GreenPrint("Hint: run [n -c] or [nh -c] or start sulfur with the -c option (sulfur (...) -c) to enter color mode where some items are easier to tell apart.")
                        print(*[GetRandomColor(p) for p in "This line will appear colorful in color mode. Try it yourself!".split(" ")])
                        print("\nList of colors (for Color object):")
                        print(*[f"{k}: {v}" for k, v in ANSI_COLORS.keys()], "24-bit colors are also supported.", sep="\n")
                    elif q in ["au", "cr"]:
                        GreenPrint(__doc__)
                    elif viewer_mode:
                        RedPrint(f"\033[91mUnknown command or insufficient permissions to run: [{q}]\033[0m", exit_after=False)
                    elif q.startswith("nh"):
                        GreenPrint("Relaunching sulfur here...")
                        os.system(f"{executable} -m sulfur {node.GetPath()} {q.removeprefix('nh')}")
                        exit()
                    elif q.startswith("n"):
                        GreenPrint("Relaunching sulfur...")
                        os.system(f"{executable} -m sulfur {q.removeprefix('n')}")
                        exit()
                    elif q == "xp":
                        GreenPrint("Export process started.")
                        def Iterate(p: str) -> None:
                            for f in File(p).GetChildren():
                                f = File(f)
                                if f.GetType() == "Comment":
                                    continue
                                GreenPrint(f"Exporting: {f.GetPath()}")
                                shutil.copy(os.path.join(f.GetPath(), "__Content__"), os.path.join(f"{node.GetName()}.export", f"{f.GetName()}.{f.GetType().replace(':', '-').lower()}"))
                                Iterate(f.GetPath())
                        if os.path.exists(f"{node.GetName()}.export"):
                            RedPrint(f"{node.GetName()}.export already exists! Delete it with the [rmxp] command or move it manually first before making a new export.", exit_after=False)
                        os.mkdir(f"{node.GetName()}.export")
                        Iterate(node.GetPath())
                        GreenPrint(f"Export completed! See results in {node.GetName()}.export")
                    elif q == "rmxp":
                        if os.path.exists(f"{node.GetName()}.export"):
                            shutil.rmtree(f"{node.GetName()}.export", onerror=ForceRemove)
                            GreenPrint("Current export deleted.")
                        else:
                            RedPrint("No export to delete!", exit_after=False)
                    elif q in ["reset", "reset+q"]:
                        RedPrint(f"/!\\ Are you sure you want to delete ALL objects in \033[3m{node.GetPath()}\033[0m", exit_after=False)
                        try:
                            while True:
                                q2: str = input(f"Type the following to confirm: \033[3m{node.GetName()}\033[0m > ")
                                if q2 == node.GetName():
                                    try:
                                        os.remove(os.path.join(node.GetPath(), "__Content__"))
                                        os.remove(os.path.join(node.GetPath(), "__Type__"))
                                        shutil.rmtree(os.path.join(node.GetPath(), "__Children__"), onerror=ForceRemove)
                                    except FileNotFoundError:
                                        ...
                                    if q == "reset+q":
                                        GreenPrint("Reset completed. Exiting Sulfur...")
                                        exit()
                                    GreenPrint("Reset completed. Restarting Sulfur...")
                                    os.system(f"{executable} -m sulfur {node.GetPath()}")
                                    exit()
                                else:
                                    raise KeyboardInterrupt
                        except (KeyboardInterrupt, EOFError):
                            RedPrint("Operation cancelled.", exit_after=False)
                    elif q == "spm":
                        print("\033[93m[spm]\033[0m entered spm command prompt. use commands like enable, disable, enable-all,\ndisable-all, list-enabled, list-disabled or list to navigate your sulfur plugins")
                        GreenPrint("ctrl+c to exit spm")
                        while True:
                            try:
                                q4: str = input("\033[93m[spm]\033[0m [cmd] ")
                                q4cmd, *q4args = q4.split(" ")
                                try:
                                    if q4cmd == "enable":
                                        if q4args[0] in [plugin.name for plugin in Plugin.GetPlugins()]:
                                            Plugin(q4args[0], q4args[0] in [plugin.name for plugin in Plugin.GetEnabledPlugins()]).Enable()
                                            print(f"\033[1;93m[spm]\033[0m restart sulfur using [nh] (or [n]) to apply changes")
                                        else:
                                            RedPrint(f"[spm] plugin '{q4args[0]}' is not installed.", exit_after=False)
                                    elif q4cmd == "disable":
                                        if q4args[0] in [plugin.name for plugin in Plugin.GetPlugins()]:
                                            Plugin(q4args[0], q4args[0] in [plugin.name for plugin in Plugin.GetEnabledPlugins()]).Disable()
                                            print(f"\033[1;93m[spm]\033[0m restart sulfur using [nh] (or [n]) to apply changes")
                                        else:
                                            RedPrint(f"[spm] plugin '{q4args[0]}' is not installed.", exit_after=False)
                                    elif q4cmd == "enable-all":
                                        for plugin in Plugin.GetDisabledPlugins():
                                            plugin.Enable()
                                        print(f"\033[1;93m[spm]\033[0m restart sulfur using [nh] (or [n]) to apply changes")
                                    elif q4cmd == "disable-all":
                                        for plugin in Plugin.GetEnabledPlugins():
                                            plugin.Disable()
                                        print(f"\033[1;93m[spm]\033[0m restart sulfur using [nh] (or [n]) to apply changes")
                                    elif q4cmd == "list-enabled":
                                        print("\033[1;93m[spm]\033[0m list of enabled plugins:")
                                        for plugin in Plugin.GetEnabledPlugins():
                                            print(f"- {GetRandomColor(plugin.name, force=True)}")
                                    elif q4cmd == "list-disabled":
                                        print("\033[1;93m[spm]\033[0m list of disabled plugins:")
                                        for plugin in Plugin.GetDisabledPlugins():
                                            print(f"- {GetRandomColor(plugin.name, force=True)}")
                                    elif q4cmd == "list":
                                        print("\033[1;93m[spm]\033[0m list of all installed plugins:")
                                        for plugin in Plugin.GetPlugins():
                                            print(f"- {GetRandomColor(plugin.name, force=True)} \033[90m({'enabled' if plugin.enabled else 'disabled'})\033[0m")
                                    elif q4cmd in ["nh", "n"]:
                                        RedPrint(f"[spm] command [{q4cmd}] cannot be run in spm mode, press ctrl-c and try again.", exit_after=False)
                                    elif not q4:
                                        ...
                                    else:
                                        RedPrint(f"[spm] unknown command: [{q4cmd}]", exit_after=False)
                                except IndexError:
                                    RedPrint(f"[spm] not enough arguments provided. syntax: {q4cmd} <pluginName>", exit_after=False)
                            except (KeyboardInterrupt, EOFError):
                                print()
                                break
                    elif commands.get(q) is not None:
                        commands[q]()
                    elif not q:
                        ...
                    else:
                        RedPrint(f"Unknown command: [{q}]", exit_after=False)
            except (KeyboardInterrupt, EOFError):
                ...
        return order, commands
    @staticmethod
    def AddChild(parent: File, name: str, file_type: str, content: str):
        name = name.strip("/\\ \t")
        name = name if name and "/" not in name and "\\" not in name else file_type.split(":")[-1]
        child_dir = os.path.join(parent.GetPath(), "__Children__", name)
        if os.path.exists(child_dir):
            RedPrint(f"Object of name '{name}' already exists in that location! Delete it first if you want to overwrite it.", exit_after=False)
        os.makedirs(child_dir)
        with open(os.path.join(child_dir, "__Type__"), 'w') as f:
            f.write(file_type)
        with open(os.path.join(child_dir, "__Content__"), 'w') as f:
            f.write(content)
        os.makedirs(os.path.join(child_dir, "__Children__"))
        return child_dir
    @staticmethod
    def DeleteChild(parent: File, name: str):
        child_dir = parent.GetChild(name).GetPath()
        if not os.path.exists(child_dir):
            RedPrint(f"No such object: {name} at {child_dir}", exit_after=False)
        shutil.rmtree(child_dir, onerror=ForceRemove)
    @staticmethod
    def RenameChild(parent: File, name: str, new_name: str):
        child_dir = parent.GetChild(name).GetPath()
        if not os.path.exists(child_dir):
            RedPrint(f"No such object: {name} at {child_dir}", exit_after=False)
        new_name = new_name.strip("/\\ \t")
        new_name = new_name if new_name and "/" not in new_name and "\\" not in new_name else parent.GetChild(name).GetType()
        os.rename(child_dir, os.path.join(child_dir, "..", new_name))