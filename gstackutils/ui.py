import os

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.containers import Window, ScrollOffsets
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.mouse_events import MouseEventType


class Node:
    def __init__(
        self, node=None, key=None, repr=[("", "")], active_repr=[("", "")],
        isleaf=True, force_open=False, enterable=True,
        selectable=True, depth=0,
        decoration_closed=[("", "")],
        decoration_open=[("", "")],
    ):
        self.node = node
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
        self.visible_nodes = []
        self.open_set = set()
        self.selected_index = 0  # update needs this
        self.update()
        self.selected_index = self.next_enterable(0, 1)
        assert self.selected_index is not None

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
            self.selected_index = self.next_enterable(self.selected_index + dl, 1)

        @kb.add('pageup')
        def pageup(event):
            dl = len(self.window.render_info.displayed_lines)
            self.selected_index = self.next_enterable(self.selected_index - dl, -1)

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

        self.control = FormattedTextControl(
            self.get_text_fragments,
            key_bindings=kb,
            focusable=True,
            show_cursor=False
        )

        self.window = Window(
            content=self.control,
            # style='class:file-select',
            right_margins=[
                ScrollbarMargin(display_arrows=True),
            ],
            scroll_offsets=ScrollOffsets(5, 5)
        )

    def toggle(self, key):
        if key in self.open_set:
            self.open_set.remove(key)
        else:
            self.open_set.add(key)
        self.update()

    def close_all(self):
        while self.open_set:
            self.open_set.pop()
            self.update()

    @property
    def current_value(self):
        return self.visible_nodes[self.selected_index]

    def isopen(self, node):
        return (node.key in self.open_set) or node.force_open

    def next_enterable(self, idx, dir):
        cnt = len(self.visible_nodes)
        idx = min(max(idx, 0), cnt - 1)
        i = idx
        while True:
            if self.visible_nodes[i].enterable:
                return i
            i += dir
            if i == (cnt if dir > 0 else -1):
                break
        i = idx
        while True:
            if self.visible_nodes[i].enterable:
                return i
            i -= dir
            if i == (cnt if dir < 0 else -1):
                break
        return None

    def up(self):
        self.selected_index = self.next_enterable(self.selected_index - 1, -1)

    def down(self):
        self.selected_index = self.next_enterable(self.selected_index + 1, 1)

    def get_child_nodes(self, node=None):
        raise NotImplemented()

    def get_text_fragments(self):
        def mouse_handler(mouse_event):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                idx = mouse_event.position.y
                if self.visible_nodes[idx].enterable:
                    self.selected_index = mouse_event.position.y
            elif mouse_event.event_type == MouseEventType.SCROLL_UP:
                self.up()
            elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                self.down()

        result = []
        for i, visible_node in enumerate(self.visible_nodes):
            active = i == self.selected_index
            if self.isopen(visible_node):
                decoration = visible_node.decoration_open
            else:
                decoration = visible_node.decoration_closed
            active_repr = visible_node.active_repr + [('[SetCursorPosition]', '')]

            result.extend(decoration)
            result.extend(active_repr if active else visible_node.repr)
            result.append(('', '\n'))

        result.pop()  # Remove last newline.

        # add mouse handlers
        for i in range(len(result)):
            result[i] = (result[i][0], result[i][1], mouse_handler)

        return result

    def update(self):
        new_visible_nodes = []

        def add_children(child_nodes):
            for node in child_nodes:
                if self.selected_index >= len(new_visible_nodes):
                    self.selected_index += 1
                new_visible_nodes.append(node)
                if self.isopen(node):
                    child_nodes = self.get_child_nodes(node)
                    add_children(child_nodes)

        if not self.visible_nodes:
            child_nodes = self.get_child_nodes()
            add_children(child_nodes)
            self.visible_nodes = new_visible_nodes
            return

        deldeeper = None
        for i, visible_node in enumerate(self.visible_nodes):
            depth = visible_node.depth

            if deldeeper is not None:
                if depth > deldeeper:
                    if self.selected_index >= len(new_visible_nodes):
                        self.selected_index -= 1
                    continue
                else:
                    deldeeper = None

            new_visible_nodes.append(visible_node)

            if visible_node.isleaf:
                continue

            child_nodes = self.get_child_nodes(visible_node)

            if not child_nodes:
                continue

            nextdeeper = False
            if len(self.visible_nodes) > i + 1:
                nextdeeper = self.visible_nodes[i + 1].depth > depth

            if self.isopen(visible_node):
                if not nextdeeper:
                    add_children(child_nodes)
            else:
                deldeeper = depth

        self.visible_nodes = new_visible_nodes
        # the selected index may have changed, find a correct position
        self.selected_index = self.next_enterable(self.selected_index, 1)

    def __pt_container__(self):
        return self.window


class FileSelect(TreeSelect):
    def __init__(self, root):
        self.root = root
        super().__init__()

    def get_child_nodes(self, node=None):
        ret = []
        root = self.root if node is None else node.node
        nodes = sorted(os.listdir(root))

        if node is None:
            for i, f in enumerate(nodes):
                abspath = os.path.join(root, f)
                isdir = os.path.isdir(abspath)
                ret.append(Node(
                    node=abspath,
                    key=abspath,
                    repr=[("bold" if isdir else "", f)],
                    active_repr=[("bold reverse" if isdir else "reverse", f)],
                    isleaf=not isdir,
                    force_open=False,
                    depth=0,
                    decoration_closed=[("grey", "▶ ")] if isdir else [("", "  ")],
                    decoration_open=[("grey", "▼ ")] if isdir else [("", "  ")],
                    enterable=abspath not in ("/host/.git", "/host/tests"),
                    selectable=not isdir
                ))
        else:
            for i, f in enumerate(nodes):
                abspath = os.path.join(root, f)
                isdir = os.path.isdir(abspath)
                decoration = node.decoration_closed[:-1]  # the last is the icon
                if not decoration:  # the firt item is special
                    decoration.append(("grey", "└" if i + 1 == len(nodes) else "├"))
                else:
                    # symbols need to be replaced on the previous level
                    repl = {"└": " ", " └": "  ", "├": "│", " ├": " │"}
                    last_sty, last_str = decoration[-1]
                    decoration[-1] = (last_sty, repl[last_str])
                    decoration.append(("grey", " └" if i + 1 == len(nodes) else " ├"))

                ret.append(Node(
                    node=abspath,
                    key=abspath,
                    repr=[("bold" if isdir else "", f)],
                    active_repr=[("bold reverse" if isdir else "reverse", f)],
                    isleaf=not isdir,
                    force_open=False,
                    depth=node.depth + 1,
                    decoration_closed=decoration + [("grey", "╴▶ " if isdir else "── ")],
                    decoration_open=decoration + [("grey", "╴▼ " if isdir else "── ")],
                    enterable=abspath not in ("/host/.git", "/host/tests"),
                    selectable=not isdir
                ))
        return ret


# class SimpleSelect(TreeSelect):
#     def __init__(self, values):
#         self.values = values
#         super().__init__()
#
#     def get_child_nodes(self, node=None):
#         return [(v, True) for v in self.values]
#
#     def node_repr(self, node):
#         return node


if __name__ == '__main__':
    from prompt_toolkit.application import Application
    from prompt_toolkit.layout.layout import Layout

    kb = KeyBindings()
    select = FileSelect("/host")
    # select = SimpleSelect(["type", "random", "file"])
    # select = TreeSelect()

    @kb.add('c-c')
    def ctrlc(event):
        event.app.exit()

    @kb.add('c')
    def close_all(event):
        select.close_all()

    @kb.add('o')
    def open(event):
        select.toggle("/host/.git")
        select.toggle("/host/tests")

    application = Application(
        layout=Layout(select),
        full_screen=True,
        key_bindings=kb,
        mouse_support=True,
    )
    application.run()
    print(select.current_value.key)
