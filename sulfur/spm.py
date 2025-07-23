import os, yaml, shutil, sys

def PluginError(err: Exception, plugin: "Plugin") -> None:
    if "-v" in sys.argv:
        raise err
    from .util import RedPrint
    RedPrint(f"Error: {err}", exit_after=False)
    print(f"\033[33;3mFrequently reported error; possibly related to bad plugin syntax?\033[0m")
    print(f"\033[33;3mLikely culprit: \033[0m{plugin.name}\033[33;3m. Run '{sys.executable} -m sulfur.disable {plugin.name}' and try again.\033[0m")
    exit(1)

SEP: str = "\\" if os.name == "nt" else "/" # CODE FROM sulfur/util.py!!!!!!!!!
# cannot import due to ImportError (circular import)

PLUGIN_PATH: str = f"{__file__}{SEP}..{SEP}plugins"
def _GetEnabledPluginPaths() -> list[str]:
    return [f"{PLUGIN_PATH}{SEP}enabled{SEP}{plugin}" for plugin in os.listdir(f"{PLUGIN_PATH}{SEP}enabled")]
def _GetDisabledPluginPaths() -> list[str]:
    return [f"{PLUGIN_PATH}{SEP}disabled{SEP}{plugin}" for plugin in os.listdir(f"{PLUGIN_PATH}{SEP}disabled")]

class Plugin:
    def __init__(self, name: str, enabled: bool = True) -> None:
        self.name: str = name
        self.enabled: bool = enabled
        self.path: str = f"{PLUGIN_PATH}{SEP}{'enabled' if self.enabled else 'disabled'}{SEP}{self.name}"
    def Enable(self) -> None:
        if self.enabled:
            print(f"\033[1;93m[spm]\033[0m plugin '{self.name}' already enabled.")
        else:
            print(f"\033[1;93m[spm]\033[0m plugin '{self.name}' enabled.")
            self.enabled = True
            new_path: str = f"{PLUGIN_PATH}{SEP}enabled{SEP}{self.name}"
            shutil.copytree(self.path, new_path)
            from .util import ForceRemove
            shutil.rmtree(self.path, onerror=ForceRemove)
            self.path = new_path
    def Disable(self) -> None:
        if not self.enabled:
            print(f"\033[1;93m[spm]\033[0m plugin '{self.name}' already disabled.")
        else:
            print(f"\033[1;93m[spm]\033[0m plugin '{self.name}' disabled.")
            self.enabled = False
            new_path: str = f"{PLUGIN_PATH}{SEP}disabled{SEP}{self.name}"
            shutil.copytree(self.path, new_path)
            from .util import ForceRemove
            shutil.rmtree(self.path, onerror=ForceRemove)
            self.path = new_path
    def GetObjectTypes(self) -> list[str]:
        return [f"{self.name}:{object_type.removesuffix(".yml")}" for object_type in os.listdir(self.path)]
    @classmethod
    def FromPath(cls, path: str) -> "Plugin":
        s: str = path.removeprefix(PLUGIN_PATH).strip("/\\")
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
            return f"{PLUGIN_PATH}{SEP}{'enabled' if os.path.exists(PLUGIN_PATH+f'{SEP}enabled{SEP}'+object_type.split(':')[0]) else 'disabled'}{SEP}{object_type.split(':')[0]}{SEP}{object_type.split(':')[1]}.yml"
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
                    if (cls.ReadObjectType(cls.TraceObjectType(ot))["Execute"] or {}).get("Enabled", False):
                        l.append(ot)
                except AttributeError as err:
                    PluginError(err, plugin)
        return l
    @staticmethod
    def ReadObjectType(path: str) -> dict:
        with open(path) as file:
            content: dict = yaml.safe_load(file)
        return content