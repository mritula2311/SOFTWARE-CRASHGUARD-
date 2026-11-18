"""Append a marked block to a document, idempotent: python scripts/r7b_append.py <file> <marker> <text file>. Keeps the file's line endings."""
import sys
from pathlib import Path

f, marker, src = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
b = f.read_bytes().decode("utf-8")
crlf = "\r\n" in b
s = b.replace("\r\n", "\n")
txt = src.read_text(encoding="utf-8").strip("\n")
start, end = f"<!-- {marker}:start -->", f"<!-- {marker}:end -->"
block = f"{start}\n{txt}\n{end}\n"
if start in s:
    i, j = s.index(start), s.index(end) + len(end) + 1
    s = s[:i] + block + s[j:]
else:
    s = s.rstrip("\n") + "\n\n" + block
f.write_bytes((s.replace("\n", "\r\n") if crlf else s).encode("utf-8"))
print("ok", f)
