import os
from typing import Any
from .core import File

def Require(module: File, d: dict | None = None) -> Any:
    mod: Any = module._Require() # NOQA
    if d is not None:
        d[module.GetName()] = mod
    return mod
def GetFile(file: str) -> File:
    return File(os.path.join(file, ".."))