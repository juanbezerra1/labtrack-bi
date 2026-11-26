"""A small linter for the Power Query (M) that the generator writes.

It checks what a text scan can check: strings and delimiters are closed and balanced, and every call to a function of
the standard library names a function that exists and gives it a number of arguments it accepts. The functions come
from `resources/m_library.json`, which has the name and the parameters (and whether each is required) of the functions
the model uses, taken from Microsoft's published definitions of the standard library.

It does not parse M. `tools/check_m.cjs` does that with Microsoft's own parser; this module is what the Python tests
can run everywhere without Node.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

IDENTIFIER = re.compile(r'#"(?:[^"]|"")*"|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*')
OPENERS = {"(": ")", "{": "}", "[": "]"}


@dataclass(frozen=True)
class Signature:
    required: int
    total: int


@lru_cache(maxsize=1)
def library() -> dict[str, Signature]:
    text = resources.files("labtrack_bi").joinpath("resources/m_library.json").read_text(encoding="utf-8")
    out: dict[str, Signature] = {}
    for entry in json.loads(text):
        parameters = entry.get("functionParameters") or []
        out[entry["name"]] = Signature(sum(1 for p in parameters if p["isRequired"]), len(parameters))
    return out


@dataclass(frozen=True)
class Call:
    name: str
    arguments: int
    line: int


def _line(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def scan(code: str) -> tuple[list[Call], list[str]]:
    """The calls to namespaced functions (`Table.AddColumn(...)`) with their number of arguments, and the problems
    of strings and delimiters."""
    problems: list[str] = []
    calls: list[Call] = []
    stack: list[tuple[str, int, int]] = []  # (closing delimiter, position, commas)
    pending: list[tuple[int, str, int]] = []  # index in `stack` where a call opens -> (stack depth, name, position)
    i, n = 0, len(code)
    while i < n:
        c = code[i]
        if code.startswith("//", i):
            i = code.find("\n", i)
            i = n if i < 0 else i
            continue
        if code.startswith("/*", i):
            end = code.find("*/", i + 2)
            if end < 0:
                problems.append(f"line {_line(code, i)}: a comment is not closed")
                break
            i = end + 2
            continue
        if c == '"':
            j = i + 1
            while j < n:
                if code[j] == '"':
                    if code[j + 1 : j + 2] == '"':
                        j += 2
                        continue
                    break
                j += 1
            else:
                problems.append(f"line {_line(code, i)}: a string is not closed")
                break
            i = j + 1
            continue
        m = IDENTIFIER.match(code, i)
        if m:
            name = m.group(0)
            j = m.end()
            while j < n and code[j] in " \t":
                j += 1
            if "." in name and not name.startswith("#") and code[j : j + 1] == "(":
                pending.append((len(stack) + 1, name, i))
            i = m.end()
            continue
        if c in OPENERS:
            stack.append((OPENERS[c], i, 0))
        elif c == ",":
            if stack:
                closing, start, commas = stack[-1]
                stack[-1] = (closing, start, commas + 1)
        elif c in ")}]":
            if not stack:
                problems.append(f"line {_line(code, i)}: '{c}' closes nothing")
            else:
                closing, start, commas = stack.pop()
                if closing != c:
                    problems.append(f"line {_line(code, i)}: '{c}' where '{closing}' was expected (opened in line {_line(code, start)})")
                elif c == ")" and pending and pending[-1][0] == len(stack) + 1:
                    _, name, position = pending.pop()
                    inner = code[start + 1 : i].strip()
                    calls.append(Call(name, 0 if not inner else commas + 1, _line(code, position)))
        i += 1
    for closing, start, _ in stack:
        problems.append(f"line {_line(code, start)}: a delimiter is not closed (expected '{closing}')")
    return calls, problems


def lint(code: str, where: str) -> list[str]:
    calls, problems = scan(code)
    known = library()
    out = [f"{where}: {p}" for p in problems]
    for call in calls:
        signature = known.get(call.name)
        if signature is None:
            out.append(f"{where}: line {call.line}: {call.name} is not in the library of the model (m_library.json)")
        elif not signature.required <= call.arguments <= signature.total:
            wanted = f"{signature.required}" if signature.required == signature.total else f"{signature.required} to {signature.total}"
            out.append(f"{where}: line {call.line}: {call.name} takes {wanted} argument(s), it has {call.arguments}")
    return out
