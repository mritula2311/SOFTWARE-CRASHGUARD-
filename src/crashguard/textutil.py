"""Small text helpers shared by the document generators."""
from __future__ import annotations


def clip(s: object, n: int) -> str:
    """Shorten to at most about n characters at a word boundary and mark the cut with an ellipsis (a plain slice cuts words in half)."""
    t = str(s)
    if len(t) <= n:
        return t
    cut = t[:n].rsplit(" ", 1)[0].rstrip(" ,;:(")
    return cut + " ..."
