import os, yaml, sys # NOQA
from pathlib import Path

PLUGINS_DIR: str = Path(__file__).parent.parent.parent

def GetEnabledPlugins() -> list[str]:
    return os.listdir(str(PLUGINS_DIR / "enabled"))
def GetDisabledPlugins() -> list[str]:
    return os.listdir(str(PLUGINS_DIR / "disabled"))
def GetAllPlugins() -> list[str]:
    return GetEnabledPlugins() + GetDisabledPlugins()
def PluginEnabled(name: str) -> bool | None:
    if name in GetAllPlugins():
        return name in GetEnabledPlugins()
def GetPluginConfig(name: str) -> dict:
    if name in GetAllPlugins():
        try:
            with (PLUGINS_DIR / ("enabled" if PluginEnabled(name) else "disabled") / name / ".plugin").open() as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            return {}
def OpenPCL(loc: str | None = None) -> None:
    os.system(f'{sys.executable} -m sulfur {loc or '.'} -r pcl')