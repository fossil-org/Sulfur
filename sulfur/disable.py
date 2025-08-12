import os
from sys import argv
from .pcl import Plugin

def main() -> None:
    plugin: Plugin = Plugin(argv[1], enabled=True)
    if not os.path.exists(plugin.path):
        plugin.enabled = False
    plugin.Disable()

if __name__ == '__main__':
    main()
