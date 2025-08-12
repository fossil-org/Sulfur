import curses, sys, keyword, platform

BACKSPACE_KEY = 263
DELETE_KEY = 330
ENTER_KEYS = {10, 13}
ESCAPE_KEY = 27

def IsBackspace(key):
    return key in ('\x08', '\x7f') or key == BACKSPACE_KEY

class Editor:
    def __init__(self, stdscr, filename, highlights: list[str]):
        self.stdscr = stdscr
        self.filename = filename
        self.lines = []
        self.cursor_y = 0
        self.cursor_x = 0
        self.mode = "insert"
        self.cmd = ""
        self.highlights: list[str] = highlights
        self.LoadObject()

    def LoadObject(self):
        try:
            with open(self.filename, encoding="utf-8") as f:
                self.lines = f.read().splitlines() or [""]
        except FileNotFoundError:
            self.lines = [""]

    def SaveObject(self):
        with open(self.filename, "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines))

    def Draw(self):
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        for idx, line in enumerate(self.lines[:h - 1]):
            x = 0
            words = line.split(" ")
            for word in words:
                color = curses.color_pair(6 if word in self.highlights else 1)
                try:
                    self.stdscr.addstr(idx, x, word, color)
                except curses.error:
                    pass
                x += len(word) + 1
        if self.mode == "command":
            self.stdscr.addstr(h - 1, 0, ":" + self.cmd)
        elif self.mode == "insert":
            self.stdscr.addstr(h - 1, 0, "-- INSERT --")
        self.stdscr.move(self.cursor_y, self.cursor_x)
        self.stdscr.refresh()

    def Run(self):
        while True:
            self.Draw()
            try:
                key = self.stdscr.get_wch()
            except curses.error:
                continue

            if isinstance(key, int):
                if key == curses.KEY_UP and self.cursor_y > 0:
                    self.cursor_y -= 1
                    self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))
                elif key == curses.KEY_DOWN and self.cursor_y < len(self.lines) - 1:
                    self.cursor_y += 1
                    self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))
                elif key == curses.KEY_LEFT:
                    if self.cursor_x > 0:
                        self.cursor_x -= 1
                    elif self.cursor_y > 0:
                        self.cursor_y -= 1
                        self.cursor_x = len(self.lines[self.cursor_y])
                elif key == curses.KEY_RIGHT:
                    if self.cursor_x < len(self.lines[self.cursor_y]):
                        self.cursor_x += 1
                    elif self.cursor_y < len(self.lines) - 1:
                        self.cursor_y += 1
                        self.cursor_x = 0

            if self.mode == "normal":
                if key == "i":
                    self.mode = "insert"
                elif key == ":":
                    self.mode = "command"
                    self.cmd = ""
                elif key == "h":
                    self.cursor_x = max(0, self.cursor_x - 1)
                elif key == "l":
                    self.cursor_x = min(len(self.lines[self.cursor_y]), self.cursor_x + 1)
                elif key == "j":
                    self.cursor_y = min(len(self.lines) - 1, self.cursor_y + 1)
                    self.cursor_x = min(len(self.lines[self.cursor_y]), self.cursor_x)
                elif key == "k":
                    self.cursor_y = max(0, self.cursor_y - 1)
                    self.cursor_x = min(len(self.lines[self.cursor_y]), self.cursor_x)

            elif self.mode == "insert":
                if key == chr(ESCAPE_KEY):
                    self.mode = "normal"
                elif isinstance(key, str) and key in ('\n', '\r'):
                    line = self.lines[self.cursor_y]
                    self.lines[self.cursor_y] = line[:self.cursor_x]
                    self.lines.insert(self.cursor_y + 1, line[self.cursor_x:])
                    self.cursor_y += 1
                    self.cursor_x = 0
                elif IsBackspace(key):
                    if self.cursor_x > 0:
                        line = self.lines[self.cursor_y]
                        self.lines[self.cursor_y] = line[:self.cursor_x - 1] + line[self.cursor_x:]
                        self.cursor_x -= 1
                    elif self.cursor_x == 0 and self.cursor_y > 0:
                        prev_line = self.lines[self.cursor_y - 1]
                        self.cursor_x = len(prev_line)
                        self.lines[self.cursor_y - 1] += self.lines[self.cursor_y]
                        del self.lines[self.cursor_y]
                        self.cursor_y -= 1
                elif isinstance(key, int) and key == DELETE_KEY:
                    line = self.lines[self.cursor_y]
                    if self.cursor_x < len(line):
                        self.lines[self.cursor_y] = line[:self.cursor_x] + line[self.cursor_x + 1:]
                elif isinstance(key, str):
                    line = self.lines[self.cursor_y]
                    self.lines[self.cursor_y] = line[:self.cursor_x] + key + line[self.cursor_x:]
                    self.cursor_x += len(key)

            elif self.mode == "command":
                if key in ('\n', '\r'):
                    if self.cmd == "w":
                        self.SaveObject()
                    elif self.cmd == "q":
                        break
                    elif self.cmd == "wq":
                        self.SaveObject()
                        break
                    self.mode = "normal"
                elif IsBackspace(key):
                    self.cmd = self.cmd[:-1]
                elif isinstance(key, str):
                    self.cmd += key


def Main(stdscr, filename: str, highlights: list[str]):
    curses.curs_set(1)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(6, curses.COLOR_YELLOW, -1)
    stdscr.keypad(True)
    editor = Editor(stdscr, filename, highlights)
    editor.Run()


def Run(filename: str, highlights: list[str]):
    if platform.system() == "Windows":
        try:
            import _curses
        except ImportError:
            raise Exception("Please install the 'windows-curses' package:\n    pip install windows-curses")
    curses.wrapper(Main, filename, highlights)