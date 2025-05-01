import os
from typing import Any
from .core import VirtualFile

def Require(module: VirtualFile, d: dict) -> Any:
    mod: Any = module.Require()
    d[module.GetName()] = mod
    return mod
def GetVF(file: str) -> VirtualFile:
    return VirtualFile(os.path.join(file, ".."))