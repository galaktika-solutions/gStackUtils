import os

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.containers import Window, ScrollOffsets
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.mouse_events import MouseEventType


class FileSelect:
    def __init__(self, root):
        self.root = root
        self.curpos = 0
        self.lines = None
        self.opened = set()
        self._update_lines()

        kb = KeyBindings()

        @kb.add("up")
        def up(event):
            self.up()

        @kb.add("down")
        def down(event):
            self.down()

        @kb.add('pagedown')
        def pagedown(event):
            dl = len(self.window.render_info.displayed_lines)
            self.curpos = min(len(self.lines) - 1, self.curpos + dl)

        @kb.add('pageup')
        def pageup(event):
            dl = len(self.window.render_info.displayed_lines)
            self.curpos = max(0, self.curpos - dl)

        @kb.add("enter")
        def enter(event):
            isopen, isdir, name, absname, depth = self.lines[self.curpos]
            if not isdir:
                event.app.exit(absname)
            else:
                if self.lines[self.curpos][0]:
                    self.lines[self.curpos][0] = False
                    self.opened.remove(self.lines[self.curpos][3])
                else:
                    self.lines[self.curpos][0] = True
                    self.opened.add(self.lines[self.curpos][3])
                self._update_lines()

        self.control = FormattedTextControl(
            self._get_text_fragments,
            key_bindings=kb,
            focusable=True,
            show_cursor=False
        )

        self.window = Window(
            content=self.control,
            style='class:file-select',
            right_margins=[
                ScrollbarMargin(display_arrows=True),
            ],
            scroll_offsets=ScrollOffsets(5, 5)
        )

    def up(self):
        self.curpos = max(0, self.curpos - 1)

    def down(self):
        self.curpos = min(len(self.lines) - 1, self.curpos + 1)

    def _get_text_fragments(self):
        def mouse_handler(mouse_event):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                self.curpos = mouse_event.position.y
            elif mouse_event.event_type == MouseEventType.SCROLL_UP:
                self.up()
            elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                self.down()

        result = []
        for i, line in enumerate(self.lines):
            isopened, isdir, name, absname, depthinfo = line

            style = ""
            if i == self.curpos:
                result.append(('[SetCursorPosition]', ''))
                style = "reverse"

            if isdir:
                style += " bold"

            icon = "   "
            if isdir:
                icon = " ▼ " if isopened else " ▶ "

            depth = len(depthinfo)
            decoration = "".join([
                (" ├─" if k == depth - 1 else " │ ") if x else (" └─" if k == depth - 1 else "   ")
                for k, x in enumerate(depthinfo)
            ])
            # decoration = "  " * depth
            result.append(("grey", f"{decoration}{icon}"))
            result.append((style, f"{line[2]}"))
            result.append(('', '\n'))

        result.pop()  # Remove last newline.

        # add mouse handlers
        for i in range(len(result)):
            result[i] = (result[i][0], result[i][1], mouse_handler)

        return result

    def _update_lines(self):
        newlines = []

        def add_children(absname, depthinfo):
            lst = sorted(os.listdir(absname))
            for i, p in enumerate(lst):
                _absname = os.path.join(absname, p)
                _isdir = os.path.isdir(_absname)
                _opened = _absname in self.opened
                _di = i + 1 != len(lst)
                # initial list: depthinfo is set to None
                _depthinfo = depthinfo + [_di] if depthinfo is not None else []
                newlines.append([_opened, _isdir, p, _absname, _depthinfo])
                if _opened:
                    add_children(_absname, _depthinfo)

        if not self.lines:
            add_children(self.root, None)
            self.lines = newlines
            return

        deldeeper = None
        for i, line in enumerate(self.lines):
            isopen, isdir, name, absname, depthinfo = line
            depth = len(depthinfo)

            if deldeeper is not None:
                if depth > deldeeper:
                    continue
                else:
                    deldeeper = None

            newlines.append(line)

            if not isdir or not os.listdir(absname):
                continue

            lastline = len(self.lines) == i + 1
            nextdeeper = False if lastline else len(self.lines[i + 1][4]) > depth

            if isopen:
                if not nextdeeper:
                    add_children(absname, depthinfo)
            else:
                deldeeper = depth

        self.lines = newlines

    def __pt_container__(self):
        return self.window


if __name__ == '__main__':
    from prompt_toolkit.application import Application
    from prompt_toolkit.layout.layout import Layout

    kb = KeyBindings()

    @kb.add('c-c')
    def ctrlc(event):
        event.app.exit()

    application = Application(
        layout=Layout(
            FileSelect(root="/host/")
        ),
        full_screen=True,
        key_bindings=kb,
        mouse_support=True,
    )
    print(application.run())
