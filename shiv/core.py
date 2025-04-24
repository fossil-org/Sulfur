import os, json, shutil
from typing import List, Any

from questionary import select

from .shivim import run

class VirtualFile:
    def __init__(self, path: str):
        self.path: str = os.path.abspath(path)
        self.name: str = os.path.basename(path)
        self.file_type = None
        self.content = None
        self.loadMetadata()

    def loadMetadata(self):
        try:
            with open(os.path.join(self.path, "__Type__")) as file:
                self.file_type = file.read().strip()
            with open(os.path.join(self.path, "__Content__")) as file:
                self.content = file.read()
        except FileNotFoundError:
            self.file_type = None
            self.content = None
    def getChild(self, name: str) -> "VirtualFile | None":
        child_path = os.path.join(self.path, "__Children__", name)
        if os.path.isdir(child_path):
            return VirtualFile(child_path)
        return None
    def getChildren(self) -> List[str]:
        children_dir = os.path.join(self.path, "__Children__")
        return os.listdir(children_dir) if os.path.isdir(children_dir) else []
    def runAsScript(self) -> None:
        exec(f"""
from shiv.script_std import require
from shiv.core import VirtualFile

this: VirtualFile = VirtualFile("{self.path}")

{self.content}
""".strip())
    def __repr__(self):
        return f"{self.name} ({self.file_type or "UnknownType"})"


class FileTreeCLUI:
    def __init__(self, root_path: str):
        self.root = VirtualFile(root_path)
    def initRoot(self) -> None:
        with open(os.path.join(self.root.path, "__Content__"), "w") as file:
            file.write(
f"""
This is the WorkspaceRoot object of the SHIV environment at {os.path.abspath(self.root.path)}.

Learn more about SHIV here: https://github.com/fossil-org/SHIV.

External changes made to this file will be reset when the SHIV CLI is exited.
""".strip())
        with open(os.path.join(self.root.path, "__Type__"), "w") as file:
            file.write(f"WorkspaceRoot")
        self.root.loadMetadata()
    def display(self, node: VirtualFile | None = None, indent: int = 0, order: int = 0, commands: dict[str, Any] | None = None) -> (int, dict[str, Any]):
        node = node or self.root
        print("  " * indent + repr(node),
              f" execute: [{order}]" if node.file_type == "LocalScript" else f" execute: \033[9m[{order}]\033[0m (Only objects of type LocalScript can be executed)",
              f" view/edit: [e{order}]",
              f" delete: [d{order}]" if indent != 0 else f" delete: \033[9m[d{order}]\033[0m (WorkspaceRoot cannot be deleted)",
              f" rename: [r{order}]" if indent != 0 else f" rename: \033[9m[r{order}]\033[0m (WorkspaceRoot cannot be renamed; rename manually instead)")
        commands = (commands or {}) | {
            "q": exit,
            "c": lambda: (os.system("clear"), self.display(), exit()),
            f"e{order}": lambda: (run(os.path.join(node.path, "__Content__")), print("Modification Commited."), self.display(), exit())
        }
        if node.file_type == "LocalScript":
            commands[str(order)] = lambda: (node.runAsScript(), print("Operation complete."), self.display(), exit())
        else:
            commands[str(order)] = lambda: print("Operation failed; only objects of type LocalScript can be executed.")
        if indent != 0:
            commands[f"r{order}"] = lambda: (self.renameChild(VirtualFile(os.path.join(node.path, "..", "..")), node.name, input("New Name: ")), print("Successfully renamed object."), self.display(), exit())
        else:
            commands[f"r{order}"] = lambda: print("WorkspaceRoot cannot be renamed; rename manually instead.")
        if indent != 0:
            commands[f"d{order}"] = lambda: (self.removeChild(VirtualFile(os.path.join(node.path, "..", "..")), node.name), print("Successfully removed object."), self.display(), exit())
        else:
            commands[f"d{order}"] = lambda: print("WorkspaceRoot cannot be deleted.")
        for child_name in node.getChildren():
            child = node.getChild(child_name)
            if child:
                new_order, new_commands = self.display(child, indent + 1, order + 1, commands)
                order = new_order
                commands = new_commands
        add_order: int = indent
        while True:
            if commands.get(f"a{add_order}") is not None:
                add_order += 1
                continue
            break
        print("  " * indent + f"  add child: [a{add_order}]")
        commands[f"a{add_order}"] = lambda: (run(os.path.join(self.addChild(node, input("Child Name: ", ), select("Child Type:", [
            "LocalScript",
            "LocalModule",
            "Folder",
            "Package",
            "Markdown",
            "String"
        ]).ask(), "Press i to start writing. Type :q to quit, :w to save, and :wq to save and quit."), "__Content__")), print(f"Successfully created object."), self.display(), exit())
        if not indent:
            try:
                while True:
                    q: str = input("[cmd] ")
                    if commands.get(q) is not None:
                        commands[q]()
                    elif not q:
                        ...
                    else:
                        print(f"Unknown command: [{q}]")
            except (KeyboardInterrupt, EOFError):
                ...
        return order, commands
    def addChild(self, parent: VirtualFile, name: str, file_type: str, content: str):
        child_dir = os.path.join(parent.path, "__Children__", name)
        os.makedirs(child_dir, exist_ok=True)
        with open(os.path.join(child_dir, "__Type__"), 'w') as f:
            f.write(file_type)
        with open(os.path.join(child_dir, "__Content__"), 'w') as f:
            f.write(content)
        os.makedirs(os.path.join(child_dir, "__Children__"), exist_ok=True)
        return child_dir
    def removeChild(self, parent: VirtualFile, name: str):
        child_dir = os.path.join(parent.path, "__Children__", name)
        if not os.path.exists(child_dir):
            raise FileNotFoundError(f"No such object: {name} at {child_dir}")
        shutil.rmtree(child_dir)
    def renameChild(self, parent: VirtualFile, name: str, new_name: str):
        child_dir = os.path.join(parent.path, "__Children__", name)
        if not os.path.exists(child_dir):
            raise FileNotFoundError(f"No such object: {name} at {child_dir}")
        os.rename(child_dir, os.path.join(child_dir, "..", new_name))