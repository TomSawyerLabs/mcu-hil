import re
BS = chr(92)
TOK = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))')
def parse(s):
    stack = [[]]; pos = 0; n = len(s)
    while pos < n:
        m = TOK.match(s, pos)
        if not m or m.end() == pos: break
        pos = m.end()
        if m.group(1): stack.append([])
        elif m.group(2): x = stack.pop(); stack[-1].append(x)
        elif m.group(3) is not None: stack[-1].append(m.group(3))
        elif m.group(4): stack[-1].append(m.group(4))
    return stack[0][0]
def find(node, key): return [c for c in node if isinstance(c, list) and c and c[0] == key]
def first(node, key):
    r = find(node, key); return r[0] if r else None
