import os

from importlib.util import module_from_spec, spec_from_file_location
from importlib.machinery import SourceFileLoader

def require(module):
    if module.file_type != "LocalModule":
        raise TypeError("Only objects of type LocalModule can be required in a script.")

    content_path: str = os.path.join(module.path, "__Content__")
    loader = SourceFileLoader(module.name, content_path)
    spec = spec_from_file_location(module.name, content_path, loader=loader)

    # loader is necessary, spec_from_file_location returns None if the loader is not specified for some reason

    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load module {module.name} from {content_path}")

    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod