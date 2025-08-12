import shutil, os
from sys import argv
from .pcl import Plugin
from .util import SEP

def main() -> None:
    paths: list[str] = argv[1:]
    for path in paths:
        name: str = os.path.basename(path)
        dst: str = f"{__file__}{SEP}..{SEP}plugins{SEP}disabled{SEP}{name}"
        update: bool = os.path.exists(dst)
        try:
            shutil.copytree(path, dst, dirs_exist_ok=True)
        except (FileNotFoundError, NotADirectoryError):
            print("\033[91m[pcl] plugin source path does not exist or is not a directory.\033[0m")
            exit(1)
        print(f"\033[1;93m[pcl]\033[0m successfully {'updated' if update else 'installed'} '{name}'")
if __name__ == '__main__':
    main()