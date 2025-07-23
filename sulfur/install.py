import shutil, os
from sys import argv
from .spm import Plugin
from .util import SEP

def main() -> None:
    paths: list[str] = argv[1:]
    for path in paths:
        name: str = os.path.basename(path)
        dst: str = f"{__file__}{SEP}..{SEP}plugins{SEP}disabled{SEP}{name}"
        update: bool = os.path.exists(dst)
        shutil.copytree(path, dst, dirs_exist_ok=True)
        print(f"\033[1;93m[spm]\033[0m successfully {'updated' if update else 'installed'} '{name}'")

if __name__ == '__main__':
    main()