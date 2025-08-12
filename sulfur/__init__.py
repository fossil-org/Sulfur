import os
from typing import Any
from .core import Object

def Require(module: Object, d: dict | None = None) -> Any:
    mod: Any = module._Require() # NOQA
    if d is not None:
        d[module.GetName()] = mod
    return mod
def GetObject(file: str) -> Object:
    return Object(os.path.join(file, ".."))