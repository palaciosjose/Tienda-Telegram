BLOCKS = "▁▂▃▄▅▆▇█"

def sparkline(values):
    """Return a small ASCII sparkline for a list of numeric values."""
    if not values:
        return ""
    mn = min(values)
    mx = max(values)
    if mn == mx:
        return BLOCKS[0] * len(values)
    scale = (len(BLOCKS) - 1) / (mx - mn)
    return ''.join(BLOCKS[int((v - mn) * scale)] for v in values)
