import pathlib, sys
r = pathlib.Path(".")
def w(p,c):(r/p).write_text(c);print(f"  OK {p}")
M = chr(10).join
