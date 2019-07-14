import os

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.containers import Window, ScrollOffsets
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.mouse_events import MouseEventType


class Node:
    """Dataclass to store node objects."""

    def __init__(
        self, value=None, key=None, repr=[("", "")], active_repr=[("", "")],
        isleaf=True, force_open=False, enterable=True,
        selectable=True, depth=0,
        decoration_closed=[("", "")],
        decoration_open=[("", "")],
    ):
        self.value = value
        self.key = key
        self.repr = repr
        self.active_repr = active_repr
        self.isleaf = isleaf
        self.force_open = force_open
        self.depth = depth
        self.decoration_closed = decoration_closed
        self.decoration_open = decoration_open
        self.enterable = enterable
        self.selectable = selectable


class TreeSelect:
    def __init__(self):
        self._visible_nodes = []
        self._open_set = set()
        self._selected_index = 0  # update needs this
        self._update()
        self._selected_index = self._next_enterable(0, 1)
        assert self._selected_index is not None

        kb = KeyBindings()

        @kb.add("up")
        def up(event):
            self.up()

        @kb.add("down")
        def down(event):
            self.down()

        @kb.add('pagedown')
        def pagedown(event):
            self.down(len(self.window.render_info.displayed_lines))

        @kb.add('pageup')
        def pageup(event):
            self.up(len(self.window.render_info.displayed_lines))

        @kb.add("enter")
        def enter(event):
            curr = self.current_value
            if curr.selectable:
                event.app.exit()
            not curr.isleaf and self.toggle(curr.key)

        @kb.add("space")
        def space(event):
            curr = self.current_value
            not curr.isleaf and self.toggle(curr.key)

        @kb.add('c')
        def close_all(event):
            self.close_all()

        self.control = FormattedTextControl(
            self._get_text_fragments,
            key_bindings=kb,
            focusable=True,
            show_cursor=False
        )

        self.window = Window(
            content=self.control,
            # style='class:file-select',
            right_margins=[ScrollbarMargin(display_arrows=True)],
            scroll_offsets=ScrollOffsets(5, 5)
        )

    def toggle(self, key):
        if key in self._open_set:
            self._open_set.remove(key)
        else:
            self._open_set.add(key)
        self._update()

    def close_all(self):
        while self._open_set:
            self._open_set.pop()
            self._update()

    @property
    def current_value(self):
        return self._visible_nodes[self._selected_index]

    def _isopen(self, node, open_all=False):
        if open_all and node.key not in self._open_set and not node.isleaf:
            self._open_set.add(node.key)
        return not node.isleaf and (node.key in self._open_set or node.force_open)

    def _next_enterable(self, idx, dir):
        """Search given direction first and backwards later."""
        cnt = len(self._visible_nodes)
        idx = min(max(idx, 0), cnt - 1)
        for _dir in (dir, -dir):
            i = idx
            while i >= 0 and i < cnt:
                if self._visible_nodes[i].enterable:
                    return i
                i += _dir
        return None

    def up(self, n=1):
        self._selected_index = self._next_enterable(self._selected_index - n, -1)

    def down(self, n=1):
        self._selected_index = self._next_enterable(self._selected_index + n, 1)

    def get_child_nodes(self, node=None):
        raise NotImplemented()

    def _get_text_fragments(self):
        def mouse_handler(mouse_event):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                idx = mouse_event.position.y
                if self._visible_nodes[idx].enterable:
                    self._selected_index = mouse_event.position.y
            elif mouse_event.event_type == MouseEventType.SCROLL_UP:
                self.up()
            elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                self.down()

        result = []
        for i, node in enumerate(self._visible_nodes):
            if self._isopen(node):
                decoration = node.decoration_open
            else:
                decoration = node.decoration_closed
            result.extend(decoration)

            if i == self._selected_index:
                repr = node.active_repr + [('[SetCursorPosition]', '')]
            else:
                repr = node.repr
            result.extend(repr)
            result.append(('', '\n'))

        result.pop()  # Remove last newline.

        # add mouse handlers
        for i in range(len(result)):
            result[i] = (result[i][0], result[i][1], mouse_handler)

        return result

    def _update(self, open_all=False):
        new_visible_nodes = []

        def add_children(child_nodes):
            for node in child_nodes:
                if self._selected_index >= len(new_visible_nodes):
                    self._selected_index += 1
                new_visible_nodes.append(node)
                if self._isopen(node, open_all):
                    child_nodes = self.get_child_nodes(node)
                    add_children(child_nodes)

        if not self._visible_nodes:
            child_nodes = self.get_child_nodes()
            add_children(child_nodes)
            self._visible_nodes = new_visible_nodes
            return

        deldeeper = None
        for i, node in enumerate(self._visible_nodes):
            depth = node.depth

            if deldeeper is not None:
                if depth > deldeeper:
                    if self._selected_index >= len(new_visible_nodes):
                        self._selected_index -= 1
                    continue
                else:
                    deldeeper = None

            new_visible_nodes.append(node)

            if node.isleaf:
                continue

            child_nodes = self.get_child_nodes(node)

            if not child_nodes:
                continue

            nextdeeper = False
            if len(self._visible_nodes) > i + 1:
                nextdeeper = self._visible_nodes[i + 1].depth > depth

            if self._isopen(node, open_all):
                if not nextdeeper:
                    add_children(child_nodes)
            else:
                deldeeper = depth

        self._visible_nodes = new_visible_nodes
        # the selected index may have changed, find a correct position
        self._selected_index = self._next_enterable(self._selected_index, 1)

    def __pt_container__(self):
        return self.window


class FileSelect(TreeSelect):
    DECORATION_REPLACE = {"└": " ", " └": "  ", "├": "│", " ├": " │"}

    def __init__(self, root):
        self.root = root
        super().__init__()

    def get_child_nodes(self, node=None):
        ret = []
        root = self.root if node is None else node.value
        nodes = sorted(os.listdir(root))

        for i, f in enumerate(nodes):
            abspath = os.path.join(root, f)
            isdir = os.path.isdir(abspath)
            depth = 0 if node is None else node.depth + 1
            # the decoration
            if node is None:
                decoration = []
            else:
                decoration = node.decoration_closed[:-1]  # the last is the icon
                if not decoration:  # the firt item is special
                    decoration.append(("grey", "└" if i + 1 == len(nodes) else "├"))
                else:
                    # symbols need to be replaced on the previous level
                    last_sty, last_str = decoration[-1]
                    decoration[-1] = (last_sty, self.DECORATION_REPLACE[last_str])
                    decoration.append(("grey", " └" if i + 1 == len(nodes) else " ├"))
            # the icon
            if node is None:
                closed_icon = [("grey", "▶ ")] if isdir else [("", "  ")]
                open_icon = [("grey", "▼ ")] if isdir else [("", "  ")]
            else:
                closed_icon = [("grey", "╴▶ " if isdir else "── ")]
                open_icon = [("grey", "╴▼ " if isdir else "── ")]

            decoration_closed = decoration + closed_icon
            decoration_open = decoration + open_icon

            ret.append(Node(
                value=abspath, key=abspath,
                repr=[("bold" if isdir else "", f)],
                active_repr=[("bold reverse" if isdir else "reverse", f)],
                isleaf=not isdir, force_open=False, depth=depth,
                decoration_closed=decoration_closed, decoration_open=decoration_open,
                enterable=True, selectable=not isdir
            ))
        return ret


class SimpleSelect(TreeSelect):
    def __init__(self, values):
        self.values = values
        super().__init__()

    def get_child_nodes(self, node=None):
        return [
            Node(value=v, key=v, repr=[(" ", v)], active_repr=[("reverse", v)])
            for v in self.values
        ]


if __name__ == '__main__':
    from prompt_toolkit.application import Application
    from prompt_toolkit.layout.layout import Layout

    kb = KeyBindings()
    select = FileSelect("/host")
    # select = SimpleSelect(["type", "random", "file"])

    @kb.add('c-c')
    def ctrlc(event):
        event.app.exit()

    application = Application(
        layout=Layout(select),
        full_screen=True,
        key_bindings=kb,
        mouse_support=True,
    )
    application.run()
    print(select.current_value.key)
