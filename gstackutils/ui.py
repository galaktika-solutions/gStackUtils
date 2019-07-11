import os

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.containers import Window, ScrollOffsets
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.mouse_events import MouseEventType


class VisibleNode:
    def __init__(self, node, isleaf, isopen, depthinfo):
        self.node = node
        self.isleaf = isleaf
        self.isopen = isopen
        self.depthinfo = depthinfo


class TreeSelect:
    def __init__(self):
        self.selected_index = 0
        self.visible_nodes = []
        self.open_set = set()
        self.update()
        self.current_value = self.visible_nodes[self.selected_index].node

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
            self.selected_index = min(
                len(self.visible_nodes) - 1,
                self.selected_index + dl
            )
            self.current_value = self.visible_nodes[self.selected_index].node

        @kb.add('pageup')
        def pageup(event):
            dl = len(self.window.render_info.displayed_lines)
            self.selected_index = max(0, self.selected_index - dl)
            self.current_value = self.visible_nodes[self.selected_index].node

        @kb.add("enter")
        def enter(event):
            visible_node = self.visible_nodes[self.selected_index]
            if visible_node.isleaf:
                return

            if visible_node.isopen:
                self.open_set.remove(visible_node.node)
            else:
                self.open_set.add(visible_node.node)
            visible_node.isopen = not visible_node.isopen
            self.update()

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

    def up(self):
        self.selected_index = max(0, self.selected_index - 1)
        self.current_value = self.visible_nodes[self.selected_index].node

    def down(self):
        self.selected_index = min(len(self.visible_nodes) - 1, self.selected_index + 1)
        self.current_value = self.visible_nodes[self.selected_index].node

    def get_child_nodes(self, node=None):
        """Returns a list of 2 tuples: (node, isleaf)."""
        node = node or "root"
        return [(f"{node}_leaf", True), (f"{node}_1", False), (f"{node}_2", False)]

    def node_repr(self, node):
        return str(node)

    def get_text_fragments(self):
        def mouse_handler(mouse_event):
            if mouse_event.event_type == MouseEventType.MOUSE_UP:
                self.selected_index = mouse_event.position.y
                self.current_value = self.visible_nodes[self.selected_index].node
            elif mouse_event.event_type == MouseEventType.SCROLL_UP:
                self.up()
            elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                self.down()

        result = []
        for i, visible_node in enumerate(self.visible_nodes):
            depth = len(visible_node.depthinfo)

            style = ""
            if i == self.selected_index:
                result.append(('[SetCursorPosition]', ''))
                style += " reverse"

            if not visible_node.isleaf:
                style += " bold"

            icon = "── "
            if not visible_node.isleaf:
                icon = "╴▼ " if visible_node.isopen else "╴▶ "
            if depth == 0:
                icon = "  "
                if not visible_node.isleaf:
                    icon = "▼ " if visible_node.isopen else "▶ "

            decoration = "".join([
                (" ├─" if k == depth - 1 else " │ ") if x else (" └─" if k == depth - 1 else "   ")
                for k, x in enumerate(visible_node.depthinfo)
            ])
            if decoration:
                decoration = decoration[1:]

            result.append(("grey", f"{decoration}{icon}"))
            result.append((style, self.node_repr(visible_node.node)))
            result.append(('', '\n'))

        result.pop()  # Remove last newline.

        # add mouse handlers
        for i in range(len(result)):
            result[i] = (result[i][0], result[i][1], mouse_handler)

        return result

    def update(self):
        new_visible_nodes = []

        def add_children(child_nodes, depthinfo):
            for i, (child_node, isleaf) in enumerate(child_nodes):
                opened = child_node in self.open_set
                hasnext = i + 1 < len(child_nodes)
                _depthinfo = [] if depthinfo is None else (depthinfo + [hasnext])
                new_visible_nodes.append(
                    VisibleNode(child_node, isleaf, opened, _depthinfo)
                )
                if opened:
                    child_nodes = self.get_child_nodes(child_node)
                    add_children(child_nodes, _depthinfo)

        if not self.visible_nodes:
            child_nodes = self.get_child_nodes()
            add_children(child_nodes, None)
            self.visible_nodes = new_visible_nodes
            return

        deldeeper = None
        for i, visible_node in enumerate(self.visible_nodes):
            depth = len(visible_node.depthinfo)

            if deldeeper is not None:
                if depth > deldeeper:
                    continue
                else:
                    deldeeper = None

            new_visible_nodes.append(visible_node)

            if visible_node.isleaf:
                continue

            child_nodes = self.get_child_nodes(visible_node.node)

            if not child_nodes:
                continue

            nextdeeper = False
            if len(self.visible_nodes) > i + 1:
                nextdeeper = len(self.visible_nodes[i + 1].depthinfo) > depth

            if visible_node.isopen:
                if not nextdeeper:
                    add_children(child_nodes, visible_node.depthinfo)
            else:
                deldeeper = depth

        self.visible_nodes = new_visible_nodes

    def __pt_container__(self):
        return self.window


class FileSelect(TreeSelect):
    def __init__(self, root):
        self.root = root
        super().__init__()

    def get_child_nodes(self, node=None):
        node = node or (self.root, "")
        dir = os.path.join(*node)  # node[0], node[1]
        lst = sorted(os.listdir(dir))
        return [((dir, x), not os.path.isdir(os.path.join(dir, x))) for x in lst]

    def node_repr(self, node):
        return node[1]


class SimpleSelect(TreeSelect):
    def __init__(self, values):
        self.values = values
        super().__init__()

    def get_child_nodes(self, node=None):
        return [(v, True) for v in self.values]

    def node_repr(self, node):
        return node


if __name__ == '__main__':
    from prompt_toolkit.application import Application
    from prompt_toolkit.layout.layout import Layout

    kb = KeyBindings()

    @kb.add('c-c')
    def ctrlc(event):
        event.app.exit()

    select = FileSelect("/host")
    application = Application(
        layout=Layout(select),
        full_screen=True,
        key_bindings=kb,
        mouse_support=True,
    )
    application.run()
    print(select.current_value)

    # select = SimpleSelect(["type", "random", "file"])
    # application = Application(
    #     layout=Layout(select),
    #     full_screen=True,
    #     key_bindings=kb,
    #     mouse_support=True,
    # )
    # application.run()
    # print(select.current_value)
