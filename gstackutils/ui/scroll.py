import os

import urwid


class Node:
    def __init__(self, value, open=False, parent=None, isleaf=True):
        self.value = value
        self.open = open
        self.parent = parent
        self.isleaf = isleaf

        self.children = []

    @property
    def num_below(self):
        if not self.open:
            return 0
        return sum([c.num_below for c in self.children]) + len(self.children)

    def islast(self, node):
        if self.children and self.children[-1] == node:
            return True
        return False

    def add_child(self, node):
        self.children.append(node)

    def remove_child(self, idx):
        self.children.pop(idx)

    def decoration(self, istarget=True):
        if not self.parent:
            return ""
        if istarget:
            if self.parent.islast(self):
                last = " └"
            else:
                last = " ├"
        else:
            if self.parent.islast(self):
                last = "  "
            else:
                last = " │"
        return self.parent.decoration(istarget=False) + last

    def node_at(self, idx):
        for c in self.children:
            if idx == 0:
                return c
            idx -= 1
            if c.num_below > idx:
                return c.node_at(idx)
            idx -= c.num_below

    @property
    def position(self):
        if not self.parent:
            return -1
        if not self.parent.open:
            raise ValueError()
        idx = self.parent.children.index(self)
        children_before = sum([c.num_below + 1 for c in self.parent.children[:idx]])
        return self.parent.position + children_before + 1

    @property
    def abspath(self):
        if not self.parent:
            return self.value
        return os.path.join(self.parent.abspath, self.value)

    def _open(self, walker, current_node):
        if self.open:
            return
        self.open = True
        if not self.children:
            walker.populate(self)
        walker.focus = current_node.position
        walker._modified()

    def _close(self, walker, current_node):
        if not self.open:
            return
        self.open = False
        node = current_node
        while True:
            try:
                walker.focus = node.position
                walker._modified()
                break
            except ValueError:
                node = node.parent


class Scrollbar(urwid.Widget):
    _sizing = frozenset(['box'])
    _selectable = False

    def render(self, size, focus=False):
        w, h = size
        text = [b" "] * h
        attr = [[("scrollbar_bg", 1)]] * h
        return urwid.canvas.TextCanvas(text, attr)


class Scroller(urwid.WidgetWrap):
    def __init__(self, listbox):
        self.listbox = listbox
        self.scrollbar = Scrollbar()
        self.columns = urwid.Columns([listbox])
        super().__init__(self.columns)

    def set_scrollbar(self, w):
        self.columns.contents[1:] = [(self.scrollbar, self.columns.options("given", w))]

    def render(self, size, focus=False):
        w, h = size
        if h < self.listbox._body.numrows:
            self.set_scrollbar(1)
        else:
            self.set_scrollbar(0)
        return super().render(size, focus)


class DirEntry(urwid.Widget):
    _selectable = True

    def __init__(self, node, walker):
        if not node:
            raise Exception("no node")
        self.node = node
        self.walker = walker

        # TODO: remove
        if node.value == ".git":
            self.walker.git = self.node

    def rows(*args, **kwargs):
        return 1

    def get_cursor_coords(self, size):
        return (0, 0)

    def render(self, size, focus):
        (w,) = size

        if self.node.isleaf:
            decoration = "── "
        else:
            if self.node.open:
                decoration = "╴▼ "
            else:
                decoration = "╴▶ "
        decoration = self.node.decoration() + decoration
        decoration = decoration[3:]
        if decoration.startswith("─"):
            decoration = " " + decoration[1:]
        decoration = decoration[:w]
        w -= len(decoration)

        text = self.node.value
        # text = str(self.node.position) + " " + text  # TODO: remove
        text = text[:w]
        text = text + " " * (w - len(text))

        decoration = bytes(decoration, "utf8")
        text = bytes(text, "utf8")
        attr = f"direntry_{'file' if self.node.isleaf else 'dir'}"
        if focus:
            return urwid.TextCanvas(
                [decoration + text],
                [[
                    ("direntry_decoration_focus", len(decoration)),
                    (f"{attr}_focus", len(text))
                ]],
                cursor=(0, 0)
            )
        return urwid.TextCanvas(
            [decoration + text],
            [[
                ("direntry_decoration", len(decoration)),
                (attr, len(text))
            ]]
        )

    def open(self):
        self.node._open(self.walker, self.node)

    def close(self):
        self.node._close(self.walker, self.node)

    def keypress(self, size, key):
        if key == "enter":
            if not self.node.isleaf:
                # self.walker.focus = 6  # TODO: remove
                if self.node.open:
                    self.close()
                else:
                    self.open()
                # self.node.open = not self.node.open
                # if self.node.open and not self.node.children:
                #     self.walker.populate(self.node)
                # self.walker._modified()
            else:
                return key
        elif key == "o":
            self.walker.git._open(self.walker, self.node)
        elif key == "c":
            self.walker.git._close(self.walker, self.node)
        else:
            return key


class DirWalker(urwid.ListWalker):
    def __init__(self, root="."):
        self.focus = 0
        self.root = Node(root, open=True, isleaf=False)
        self.populate(self.root)

    def populate(self, node):
        _, dirs, files = next(os.walk(node.abspath))
        entries = [(d, False) for d in dirs] + [(f, True) for f in files]
        entries.sort(key=lambda x: x[0])
        for e in entries:
            node.add_child(Node(e[0], parent=node, isleaf=e[1]))

    def __getitem__(self, position):
        return DirEntry(self.root.node_at(position), self)

    def next_position(self, position):
        if position >= self.root.num_below - 1:
            raise IndexError()
        return position + 1

    def prev_position(self, position):
        if position == 0:
            raise IndexError()
        return position - 1

    def set_focus(self, position):
        self.focus = position
        self._modified()

    @property
    def numrows(self):
        """Must be implemented to be usable with the scrollbar."""
        return self.root.num_below


if __name__ == "__main__":
    palette = [
        ("direntry_file", "", ""),
        ("direntry_dir", "bold,yellow", ""),
        ("direntry_file_focus", "standout", ""),
        ("direntry_dir_focus", "bold,standout", ""),
        ("direntry_decoration", "dark gray", ""),
        ("direntry_decoration_focus", "standout", ""),
        ("scrollbar_bg", "", "light blue")
    ]

    pile = urwid.Pile([
        urwid.Filler(urwid.Edit(b"What is your name?\n")),
        Scroller(urwid.ListBox(DirWalker())),
        urwid.Filler(urwid.Edit(b"What is your name?\n")),
        Scroller(urwid.ListBox(DirWalker())),
    ])

    # loop = urwid.MainLoop(pile)
    loop = urwid.MainLoop(pile, palette)
    # loop = urwid.MainLoop(Scroller(urwid.ListBox(DirWalker())), palette)
    loop.run()
