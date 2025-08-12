from typing import Iterable, Optional

def render_box(lines: Iterable[str], title: Optional[str] = None) -> str:
    """
    Renders a professional ASCII box with optional title.
    Compatible with Python 3.8+
    """
    if not lines:
        lines = [""]
    
    lines_list = list(lines)
    if not lines_list:
        lines_list = [""]
    
    # Calculate max width
    max_width = max(len(line) for line in lines_list)
    
    if title:
        max_width = max(max_width, len(title) + 4)
    
    max_width = max(max_width, 20)
    
    # Build box
    result = []
    result.append("┌" + "─" * (max_width + 2) + "┐")
    
    if title:
        title_line = f"│ {title.center(max_width)} │"
        result.append(title_line)
        result.append("├" + "─" * (max_width + 2) + "┤")
    
    for line in lines_list:
        content_line = f"│ {line.ljust(max_width)} │"
        result.append(content_line)
    
    result.append("└" + "─" * (max_width + 2) + "┘")
    
    return "\n".join(result)
