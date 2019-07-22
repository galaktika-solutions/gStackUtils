import os

import urwid

from gstackutils.ui import tree


class FSNode(tree.Node):
    def populate_children(self):
        top, dirs, files = next(os.walk(os.path.join(*self.value)))
        entries = [(d, False) for d in dirs] + [(f, True) for f in files]
        entries.sort(key=lambda x: x[0])
        self.children = [FSNode((top, e[0]), parent=self, isleaf=e[1]) for e in entries]

    def __str__(self):
        return self.value[1]


class Walker(tree.TreeWalker):
    NodeClass = FSNode


class FSSelectBox(urwid.ListBox):
    pass


if __name__ == "__main__":
    palette = [
        ("node_file", "", ""),
        ("node_dir", "bold,yellow", ""),
        ("node_file_focus", "standout", ""),
        ("node_dir_focus", "bold,standout", ""),
        ("node_decoration", "dark gray", ""),
        ("node_decoration_focus", "standout", ""),
        # ("scrollbar_bg", "", "light blue")
    ]

    # pile = urwid.Pile([
    #     urwid.Filler(urwid.Edit(b"What is your name?\n")),
    #     Scroller(urwid.ListBox(TreeWalker())),
    #     urwid.Filler(urwid.Edit(b"What is your name?\n")),
    #     Scroller(urwid.ListBox(TreeWalker())),
    # ])

    # loop = urwid.MainLoop(pile)
    # loop = urwid.MainLoop(pile, palette)
    loop = urwid.MainLoop(FSSelectBox(Walker()), palette)
    loop.run()
