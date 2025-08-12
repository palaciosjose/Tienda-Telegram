from typing import Iterable, List, Optional


def render_box(lines: Iterable[str], title: Optional[str] = None) -> str:
    """Render text inside a simple box for nicer messages.

    Parameters
    ----------
    lines:
        Iterable of lines to include inside the box.
    title:
        Optional title shown at the top separated by a horizontal rule.
    """
    # Ensure we have a list so it can be iterated multiple times
    if isinstance(lines, str):
        lines = [lines]
    else:
        lines = list(lines)

    width = 0
    for line in lines:
        width = max(width, len(line))
    if title:
        width = max(width, len(title))
    horiz = "─" * (width + 2)
    top = f"┌{horiz}┐"
    bottom = f"└{horiz}┘"
    out_lines: List[str] = [top]
    if title:
        out_lines.append(f"│ {title.ljust(width)} │")
        out_lines.append(f"├{horiz}┤")
    for line in lines:
        out_lines.append(f"│ {line.ljust(width)} │")
    out_lines.append(bottom)
    return "\n".join(out_lines)
