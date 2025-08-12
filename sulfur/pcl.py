import os, yaml, shutil, sys
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec

def PluginError(err: Exception, plugin: "Plugin") -> None:
    if "-v" in sys.argv:
        raise err
    from .util import RedPrint
    RedPrint(f"Error: {err}", exit_after=False)
    print(f"\033[33;3mFrequently reported error; possibly related to bad plugin syntax?\033[0m")
    print(f"\033[33;3mLikely culprit: \033[0m{plugin.name}\033[33;3m. Run 'pcldisable {plugin.name}' and try again.\033[0m")
    exit(1)

SEP: str = "\\" if os.name == "nt" else "/" # CODE FROM sulfur/util.py!!!!!!!!!
# cannot import due to ImportError (circular import)

def LoadResource(rel_path: str, dir: bool = False, contents: str | None = None) -> None:
    path: str = f"{__file__}{SEP}..{SEP}{rel_path}"
    if not os.path.exists(path):
        print(f"Loading necessary resource: {rel_path}")
        try:
            if dir:
                os.makedirs(path)
            else:
                with open(path, "w") as file:
                    file.write(contents)
        except Exception as err: # NOQA
            if "-v" in sys.argv:
                raise err
            print(f"  Failed to load {rel_path}: {err.__class__.__name__} ({err})", exit_after=False)
            exit(1)
        print(f"  Loaded {rel_path}.")

def LoadNecessaryResources() -> None:
    LoadResource("plugins/enabled", dir=True)
    LoadResource("plugins/disabled", dir=True)
    LoadResource("plugins", dir=True)
    LoadResource("sulfur.bat", dir=False, contents="@echo off;;python -m shiv;;pause".replace(";;", "\n"))

PLUGIN_PATH: str = f"{__file__}{SEP}..{SEP}plugins"
def _GetEnabledPluginPaths() -> list[str]:
    LoadNecessaryResources()
    return [f"{PLUGIN_PATH}{SEP}enabled{SEP}{plugin}" for plugin in os.listdir(f"{PLUGIN_PATH}{SEP}enabled")]
def _GetDisabledPluginPaths() -> list[str]:
    LoadNecessaryResources()
    return [f"{PLUGIN_PATH}{SEP}disabled{SEP}{plugin}" for plugin in os.listdir(f"{PLUGIN_PATH}{SEP}disabled")]

class Plugin:
    def __init__(self, name: str, enabled: bool = True) -> None:
        self.name: str = name
        self.enabled: bool = enabled
        self.path: str = f"{PLUGIN_PATH}{SEP}{'enabled' if self.enabled else 'disabled'}{SEP}{self.name}"
    def Enable(self) -> None:
        if self.enabled:
            print(f"\033[1;93m[pcl]\033[0m plugin '{self.name}' already enabled.")
        else:
            print(f"\033[1;93m[pcl]\033[0m plugin '{self.name}' enabled.")
            self.enabled = True
            new_path: str = f"{PLUGIN_PATH}{SEP}enabled{SEP}{self.name}"
            shutil.copytree(self.path, new_path)
            from .util import ForceRemove
            shutil.rmtree(self.path, onerror=ForceRemove)
            self.path = new_path
    def Disable(self) -> None:
        if not self.enabled:
            print(f"\033[1;93m[pcl]\033[0m plugin '{self.name}' already disabled.")
        else:
            print(f"\033[1;93m[pcl]\033[0m plugin '{self.name}' disabled.")
            self.enabled = False
            new_path: str = f"{PLUGIN_PATH}{SEP}disabled{SEP}{self.name}"
            shutil.copytree(self.path, new_path)
            from .util import ForceRemove
            shutil.rmtree(self.path, onerror=ForceRemove)
            self.path = new_path
    def GetDescription(self) -> str | None:
        pcl_content: dict = self.ReadConfig(f"{self.path}{SEP}.plugin")
        return pcl_content.get("Description")
    def GetObjectTypes(self) -> list[str]:
        return [f"{self.name}:{object_type.removesuffix(".objtype")}" for object_type in [i for i in os.listdir(self.path) if i.endswith(".objtype")]]
    @classmethod
    def FromPath(cls, path: str) -> "Plugin":
        s: str = os.path.abspath(path.removeprefix(PLUGIN_PATH)).strip("/\\")
        name: str = os.path.split(s)[1]
        enabled: bool = "enabled" in os.path.split(s)[0]
        return cls(name, enabled)
    @classmethod
    def GetEnabledPlugins(cls) -> "list[Plugin]":
        return [cls.FromPath(plugin) for plugin in _GetEnabledPluginPaths()]
    @classmethod
    def GetDisabledPlugins(cls) -> "list[Plugin]":
        return [cls.FromPath(plugin) for plugin in _GetDisabledPluginPaths()]
    @classmethod
    def GetPlugins(cls) -> "list[Plugin]":
        return cls.GetEnabledPlugins() + cls.GetDisabledPlugins()
    @staticmethod
    def TraceObjectType(object_type: str) -> str | None:
        if ":" in object_type:
            return f"{PLUGIN_PATH}{SEP}{'enabled' if os.path.exists(PLUGIN_PATH+f'{SEP}enabled{SEP}'+object_type.split(':')[0]) else 'disabled'}{SEP}{object_type.split(':')[0]}{SEP}{object_type.split(':')[1]}.objtype"
    @staticmethod
    def GetAllObjectTypes(plugins: "list[Plugin]") -> list[str]:
        l: list[str] = []
        for plugin in plugins:
            l += plugin.GetObjectTypes()
        return l
    @classmethod
    def GetExecutableObjectTypes(cls, plugins: "list[Plugin]") -> list[str]:
        l: list[str] = []
        for plugin in plugins:
            for ot in plugin.GetObjectTypes():
                try:
                    try:
                        if (cls.ReadConfig(cls.TraceObjectType(ot))["Execute"] or {}).get("Enabled", False):
                            l.append(ot)
                    except TypeError as err:
                        PluginError(err, Plugin.FromPath(str(Path(cls.TraceObjectType(ot)).parent)))
                except AttributeError as err:
                    PluginError(err, plugin)
        return l
    @staticmethod
    def ReadConfig(path: str) -> dict:
        #ot: str = ':'.join(path.split(SEP)[-2:]).removesuffix('.objtype')
        #if not os.path.exists(path):
        #    from .util import RedPrint
        #    RedPrint(f"[pcl] error: object type '{ot}' could not be fetched. perhaps {ot.split(':')[0]} has been disabled/uninstalled?")
        with open(path) as file:
            content: dict = yaml.safe_load(file)
        return content
    def Include(self, filename: str, req_plugin: str, req_author: str):
        if ".py" in filename:
            print(f"\033[33m[pcl] warning: possible (unsupported) file extension found during import of '{self.name}:{filename}'. make sure your file is called i.e. Script, and not Script.py.")
        path: str = f"{self.path}{SEP}{filename.replace('.', SEP)}.py"
        if not os.path.exists(path):
            from .util import RedPrint
            RedPrint(f"[pcl] error: '{self.name}:{filename}' file could not be found during import.", exit_after=False)
            return
        pcl_content: dict = self.ReadConfig(f"{self.path}{SEP}.plugin")
        matches: list[dict] = [] # {"path": str, "priority": int, "layer": int, "content": dict}
        # priority rules: 1 - wild selector, 2 - semi-specific wild selector, 3 - specific selector
        p1l: int = 0
        p2l: int = 0
        p3l: int = 0
        for en, ec in ((pcl_content.get("Permissions") or {}).get("Resources") or {}).items():
            ec = ec or {}
            if en == filename:
                matches.append({
                    "path": en,
                    "priority": 3,
                    "layer": p3l,
                    "content": ec
                })
                p3l += 1
                continue
            if en == ".*":
                matches += [{
                    "path": p,
                    "priority": 1,
                    "layer": p1l,
                    "content": ec
                } for p in os.listdir(self.path)]
                p1l += 1
                continue
            current: list[str] = []
            for section in en.split("."):
                if section.strip() == "*":
                    matches += [{
                        "path": f"{'.'.join(current)}.{p}",
                        "priority": 1,
                        "layer": p2l,
                        "content": ec
                    } for p in os.listdir(f"{self.path}{SEP}{'.'.join(current).replace('.', SEP)}")]
                    p2l += 1
                    break
                else:
                    current.append(section)
        p1m: list[dict] = [match for match in matches if match["priority"] == 1 and match["path"] == filename]
        p2m: list[dict] = [match for match in matches if match["priority"] == 2 and match["path"] == filename]
        p3m: list[dict] = [match for match in matches if match["priority"] == 3 and match["path"] == filename]
        ep: list | None = p1m if p1m else (p2m if p2m else (p3m if p3m else None))
        def PrintNoPermission() -> None:
            from .util import RedPrint
            RedPrint(f"[pcl] error: no permission to use '{self.name}:{filename}'.", exit_after=False)
        if ep is None:
            if "-v" in sys.argv:
                print(f"'{req_plugin} by {req_author}' tried to fetch a private resource.")
            PrintNoPermission()
            return
        em: dict = ep[0]
        permissions: dict = em["content"]
        if permissions.get("InheritsFrom"):
            inherited: dict | None | str = ((pcl_content.get("Permissions") or {}).get("Groups") or {}).get(permissions["InheritsFrom"], "NON-EXISTENT") or {}
            if inherited == "NON-EXISTENT":
                from .util import RedPrint
                RedPrint(f"[pcl] error: non-existent permission group with key '{permissions.get('InheritsFrom')}'", exit_after=False)
                return
            permissions = permissions | inherited
        pwe: bool = (permissions.get("PluginWhitelist") or {}).get("Enabled") or False
        pw: list[str] = (permissions.get("PluginWhitelist") or {}).get("List") or []
        awe: bool = (permissions.get("AuthorWhitelist") or {}).get("Enabled") or False
        aw: list[str] = (permissions.get("AuthorWhitelist") or {}).get("List") or []
        pbe: bool = (permissions.get("PluginBlacklist") or {}).get("Enabled") or False
        pb: list[str] = (permissions.get("PluginBlacklist") or {}).get("List") or []
        abe: bool = (permissions.get("AuthorBlacklist") or {}).get("Enabled") or False
        ab: list[str] = (permissions.get("AuthorBlacklist") or {}).get("List") or []
        if pwe and (req_plugin not in pw):
            if "-v" in sys.argv:
                print(f"'{req_plugin} by {req_author}' failed PluginWhitelist check.")
            PrintNoPermission()
            return
        if awe and (req_author not in aw):
            if "-v" in sys.argv:
                print(f"'{req_plugin} by {req_author}' failed AuthorWhitelist check.")
            PrintNoPermission()
            return
        if pbe and (req_plugin in pb):
            if "-v" in sys.argv:
                print(f"'{req_plugin} by {req_author}' failed PluginBlacklist check.")
            PrintNoPermission()
            return
        if abe and (req_author in ab):
            if "-v" in sys.argv:
                print(f"'{req_plugin} by {req_author}' failed AuthorBlacklist check.")
            PrintNoPermission()
            return
        spec = spec_from_file_location(filename.replace(".", "_"), path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        return module