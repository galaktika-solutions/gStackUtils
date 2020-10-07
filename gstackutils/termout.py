from rich import console, text, table, box, padding, print


def print_info(info, verbosity=0):
    cons = console.Console()
    for section in info:
        cons.print()
        cons.print(text.Text(section["section"]), style="bold")
        if verbosity:
            cons.print(padding.Padding(text.Text(section["help_text"] or "", style="italic"), (0, 0, 0, 4)))
        # tab = table.Table(show_header=False, box=box.SIMPLE_HEAD)
        tab = table.Table.grid(padding=(0, 1))
        for field in section["config_items"]:
            errors = table.Table.grid()
            for e in field["errors"]:
                errors.add_row(text.Text(e))
            if verbosity:
                tab.add_row(field["field"], text.Text(field["reportable"]), field["status"], errors, text.Text(field["help_text"] or "", style="italic"))
            else:
                tab.add_row(field["field"], text.Text(field["reportable"]), field["status"], errors)
        cons.print(tab)
