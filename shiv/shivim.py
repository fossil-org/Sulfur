import curses
import sys

BACKSPACE_KEY: int = 263
DELETE_KEY: int = 330

class Shivim:
    def __init__(self, stdscr, filename):
        self.stdscr = stdscr
        self.filename = filename
        self.lines = []
        self.cursor_y = 0
        self.cursor_x = 0
        self.mode = 'normal'
        self.cmd = ''
        self.load_file()

    def load_file(self):
        try:
            with open(self.filename) as f:
                self.lines = f.read().splitlines() or ['']
        except FileNotFoundError:
            self.lines = ['']

    def save_file(self):
        with open(self.filename, 'w') as f:
            f.write('\n'.join(self.lines))

    def draw(self):
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        for idx, line in enumerate(self.lines[:h - 1]):
            self.stdscr.addstr(idx, 0, line)
        if self.mode == 'command':
            self.stdscr.addstr(h - 1, 0, ':' + self.cmd)
        elif self.mode == 'insert':
            self.stdscr.addstr(h - 1, 0, "-- INSERT --")
        self.stdscr.move(self.cursor_y, self.cursor_x)
        self.stdscr.refresh()

    def run(self):
        while True:
            self.draw()
            key = self.stdscr.get_wch()

            if isinstance(key, int):
                if key == curses.KEY_UP:
                    if self.cursor_y > 0:
                        self.cursor_y -= 1
                        self.cursor_x = min(self.cursor_x, len(self.lines[self.cursor_y]))
                elif key == curses.KEY_DOWN:
                    if self.cursor_y < len(self.lines) - 1:
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

            if self.mode == 'normal':
                if key == 'i':
                    self.mode = 'insert'
                elif key == ':':
                    self.mode = 'command'
                    self.cmd = ''
                elif key == 'h':
                    self.cursor_x = max(0, self.cursor_x - 1)
                elif key == 'l':
                    self.cursor_x = min(len(self.lines[self.cursor_y]), self.cursor_x + 1)
                elif key == 'j':
                    self.cursor_y = min(len(self.lines) - 1, self.cursor_y + 1)
                    self.cursor_x = min(len(self.lines[self.cursor_y]), self.cursor_x)
                elif key == 'k':
                    self.cursor_y = max(0, self.cursor_y - 1)
                    self.cursor_x = min(len(self.lines[self.cursor_y]), self.cursor_x)

            elif self.mode == 'insert':
                if key == '\x1b':  # ESC
                    self.mode = 'normal'
                elif key == '\n':  # Enter
                    line = self.lines[self.cursor_y]
                    self.lines[self.cursor_y] = line[:self.cursor_x]
                    self.lines.insert(self.cursor_y + 1, line[self.cursor_x:])
                    self.cursor_y += 1
                    self.cursor_x = 0
                elif key == '\x7f' or key == BACKSPACE_KEY:  # Backspace
                    if self.cursor_x > 0:  # Delete character before cursor
                        line = self.lines[self.cursor_y]
                        self.lines[self.cursor_y] = line[:self.cursor_x - 1] + line[self.cursor_x:]
                        self.cursor_x -= 1
                    elif self.cursor_x == 0 and self.cursor_y > 0:  # Merge with previous line if at start of line
                        prev_line = self.lines[self.cursor_y - 1]
                        self.cursor_x = len(prev_line)
                        self.lines[self.cursor_y - 1] += self.lines[self.cursor_y]
                        del self.lines[self.cursor_y]
                        self.cursor_y -= 1
                elif key == DELETE_KEY:  # Delete key
                    line = self.lines[self.cursor_y]
                    if self.cursor_x < len(line):  # Delete character after cursor
                        self.lines[self.cursor_y] = line[:self.cursor_x] + line[self.cursor_x + 1:]
                elif isinstance(key, str):  # Any regular key (non-special)
                    line = self.lines[self.cursor_y]
                    self.lines[self.cursor_y] = line[:self.cursor_x] + key + line[self.cursor_x:]
                    self.cursor_x += 1

            elif self.mode == 'command':
                if key == '\n':  # Enter in command mode
                    if self.cmd == 'w':
                        self.save_file()
                    elif self.cmd == 'q':
                        break
                    elif self.cmd == 'wq':
                        self.save_file()
                        break
                    self.mode = 'normal'
                elif key == '\x7f' or key == BACKSPACE_KEY:  # Backspace in command mode
                    self.cmd = self.cmd[:-1]  # Remove last character from command string
                elif key == DELETE_KEY:  # Delete key in command mode
                    self.cmd = self.cmd[:self.cursor_x] + self.cmd[self.cursor_x + 1:]
                elif isinstance(key, str):  # Append any character typed to the command
                    self.cmd += key


def main(stdscr, filename):
    curses.curs_set(1)
    editor = Shivim(stdscr, filename)
    editor.run()


def run(filename):
    curses.wrapper(main, filename)
