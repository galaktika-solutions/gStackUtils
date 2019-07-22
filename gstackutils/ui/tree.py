import urwid


class Node:
    def __init__(self, value, isopen=False, parent=None, isleaf=True):
        self.value = value
        self.isopen = isopen
        self.parent = parent
        self.isleaf = isleaf
        self.children = []

    def __len__(self):
        if not self.isopen:
            return 0
        return sum([len(c) for c in self.children]) + len(self.children)

    @property
    def isroot(self):
        return self.parent is None

    def _isnthchild(self, n):
        if self.isroot:
            return False
        if self.parent.children[n] == self:
            return True
        return False

    @property
    def islast(self):
        return self._isnthchild(-1)

    @property
    def isfirst(self):
        return self._isnthchild(0)

    def populate_children(self):
        raise NotImplementedError()

    def __str__(self):
        raise NotImplementedError()

    def _next(self):
        if self.isroot:
            raise IndexError()
        if not self.islast:
            idx = self.parent.children.index(self)
            return self.parent.children[idx + 1]
        return self.parent._next()

    def next(self):
        if self.isopen and self.children:
            return self.children[0]
        return self._next()

    def _lastchild(self):
        if self.isleaf or not self.isopen or not self.children:
            return self
        return self.children[-1]._lastchild()

    def previous(self):
        if not self.isfirst:
            idx = self.parent.children.index(self)
            return self.parent.children[idx - 1]._lastchild()
        if self.parent.isroot:
            raise IndexError()
        return self.parent

    def open(self):
        if self.isopen or self.isleaf:
            return
        self.isopen = True
        if not self.children:
            self.populate_children()

    def close(self, current_node):
        if not self.isopen or self.isleaf:
            return current_node
        self.isopen = False
        # going upwards return the one that has only open ascendants
        candidate = current_node
        node = current_node
        while node.parent is not None:
            if not node.parent.isleaf and not node.parent.isopen:
                candidate = None
            elif candidate is None:
                candidate = node
            node = node.parent
        return candidate

    def open_all(self):
        self.open()
        for c in self.children:
            c.open_all()

    def close_all(self, current_node):
        cn = current_node
        if not self.isroot:
            cn = self.close(cn)
        for c in self.children:
            cn = c.close_all(cn)
        return cn


class NodeWidget(urwid.Widget):
    _selectable = True

    def __init__(self, node, walker):
        self.node = node
        self.walker = walker

    def rows(*args, **kwargs):
        return 1

    def get_cursor_coords(self, size):
        return (0, 0)

    def decoration(self, node, istarget=True):
        if node.parent is None:
            return ""
        if istarget:
            if node.islast:
                last = " └"
            else:
                last = " ├"
        else:
            if node.islast:
                last = "  "
            else:
                last = " │"
        return self.decoration(node.parent, istarget=False) + last

    def render(self, size, focus):
        (w,) = size

        if self.node.isleaf:
            decoration = "── "
        else:
            if self.node.isopen:
                decoration = "╴▼ "
            else:
                decoration = "╴▶ "
        decoration = self.decoration(self.node) + decoration
        decoration = decoration[3:]
        if decoration.startswith("─"):
            decoration = " " + decoration[1:]
        decoration = decoration[:w]
        w -= len(decoration)

        text = str(self.node)
        text = text[:w]
        text = text + " " * (w - len(text))

        decoration = bytes(decoration, "utf8")
        text = bytes(text, "utf8")
        attr = f"node_{'file' if self.node.isleaf else 'dir'}"
        if focus:
            return urwid.TextCanvas(
                [decoration + text],
                [[
                    ("node_decoration_focus", len(decoration)),
                    (f"{attr}_focus", len(text))
                ]],
                cursor=(0, 0)
            )
        return urwid.TextCanvas(
            [decoration + text],
            [[
                ("node_decoration", len(decoration)),
                (attr, len(text))
            ]]
        )

    def open(self):
        self.node.open()
        self.walker._modified()

    def close(self):
        self.walker.set_focus(self.node.close(self.walker.focus))

    def keypress(self, size, key):
        if key in ("enter",):
            if not self.node.isleaf:
                if self.node.isopen:
                    self.close()
                else:
                    self.open()
            else:
                return key
        elif key == "o":
            self.node.open_all()
            self.walker._modified()
        elif key == "c":
            self.node.close_all(self.walker.focus)
            self.walker.set_focus(self.node.close_all(self.walker.focus))
        else:
            return key


class TreeWalker(urwid.ListWalker):
    NodeClass = Node

    def __init__(self, root="."):
        self.root = self.NodeClass(("", root), isopen=True, isleaf=False)
        self.root.populate_children()
        self.focus = self.root.children[0]

    def __getitem__(self, position):
        return NodeWidget(position, self)

    def next_position(self, position):
        return position.next()

    def prev_position(self, position):
        return position.previous()

    def set_focus(self, position):
        self.focus = position
        self._modified()

    @property
    def numrows(self):
        """Must be implemented to be usable with the scrollbar."""
        return len(self.root)

    def open_all(self):
        self.root.open_all()
        self._modified()

    def close_all(self):
        self.set_focus(self.root.close_all(self.focus))
