#!/usr/bin/env python3
"""Render _cv-content.tex to standalone HTML, one mode at a time.

    tex2html.py --mode full|short|onepage [--content F] [--preamble F] > cv.html

The HTML is an intermediate for the DOCX build (see build-docx.sh); pandoc's
own LaTeX reader cannot be used directly because it expands \\ent, \\entl and
friends into their \\parshape internals and does not evaluate \\ifcvmedium.

Single source of truth stays _cv-content.tex. Only the macros that file
actually uses are implemented, and an unknown macro is a hard error -- a new
macro must be taught to this script, never silently dropped.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import html
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

MODES = ("full", "short", "onepage")
# \ifcvmedium is true for full and short; \ifcvextended only for full.
FLAGS = {
    "full": {"cvmedium": True, "cvextended": True},
    "short": {"cvmedium": True, "cvextended": False},
    "onepage": {"cvmedium": False, "cvextended": False},
}


class TexError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# lexing helpers
# --------------------------------------------------------------------------

def strip_comments(text: str) -> str:
    """Drop TeX comments. A % also eats the newline and the next line's indent."""
    out: list[str] = []
    for line in text.split("\n"):
        cut = None
        i = 0
        while i < len(line):
            if line[i] == "\\":
                i += 2
                continue
            if line[i] == "%":
                cut = i
                break
            i += 1
        if cut is None:
            out.append(line + "\n")
        elif cut == 0 and not line[:cut].strip():
            pass  # whole-line comment: contributes nothing at all
        else:
            out.append(line[:cut])  # no newline: % joins to the next line
    return "".join(out)


def read_group(s: str, i: int) -> tuple[str, int]:
    """s[i] must be '{'. Return (contents, index just past the matching '}')."""
    if i >= len(s) or s[i] != "{":
        raise TexError(f"expected '{{' at offset {i}: {s[i:i + 40]!r}")
    depth = 0
    j = i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise TexError(f"unbalanced '{{' at offset {i}: {s[i:i + 40]!r}")


def skip_ws(s: str, i: int) -> int:
    while i < len(s) and s[i] in " \t\n":
        i += 1
    return i


def read_optional(s: str, i: int) -> tuple[str | None, int]:
    """Read a [...] optional argument if one is present."""
    j = skip_ws(s, i)
    if j < len(s) and s[j] == "[":
        k = s.index("]", j)
        return s[j + 1:k], k + 1
    return None, i


# --------------------------------------------------------------------------
# \ifcvmedium / \ifcvextended
# --------------------------------------------------------------------------

COND = re.compile(r"\\(ifcvmedium|ifcvextended|else|fi)(?![a-zA-Z])")


def resolve_conditionals(text: str, mode: str) -> str:
    """Evaluate the two CV mode conditionals, keeping only the live branches."""
    flags = FLAGS[mode]
    out: list[str] = []
    stack: list[dict] = []  # {value, in_else}
    pos = 0

    def live() -> bool:
        return all(f["value"] != f["in_else"] for f in stack)

    for m in COND.finditer(text):
        if live():
            out.append(text[pos:m.start()])
        pos = m.end()
        kind = m.group(1)
        if kind.startswith("ifcv"):
            stack.append({"value": flags[kind[2:]], "in_else": False})
        elif kind == "else":
            if not stack:
                raise TexError("\\else with no matching \\if")
            stack[-1]["in_else"] = True
        else:  # \fi
            if not stack:
                raise TexError("\\fi with no matching \\if")
            stack.pop()
    if stack:
        raise TexError(f"{len(stack)} unclosed conditional(s)")
    if live():
        out.append(text[pos:])
    return "".join(out)


# --------------------------------------------------------------------------
# values lifted out of the preamble so URLs and names stay single-sourced
# --------------------------------------------------------------------------

def load_preamble_defs(preamble: str) -> dict[str, str]:
    """Pull \\newcommand{\\name}{body} bodies for the macros we mirror."""
    wanted = {"myname", "jabdc", "jabs", "jft", "jtamuga", "jutd", "cvmarks"}
    defs: dict[str, str] = {}
    for m in re.finditer(r"\\newcommand\*?\{\\([a-zA-Z]+)\}", preamble):
        name = m.group(1)
        if name not in wanted:
            continue
        body, _ = read_group(preamble, skip_ws(preamble, m.end()))
        defs[name] = body.strip()
    missing = wanted - defs.keys()
    if missing:
        raise TexError(f"preamble is missing definitions for: {sorted(missing)}")
    return defs


def ordinal_suffix(n: str) -> str:
    try:
        v = int(n)
    except ValueError:
        return "th"
    if 11 <= v % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(v % 10, "th")


# --------------------------------------------------------------------------
# inline conversion
# --------------------------------------------------------------------------

class Inline:
    """Convert the inline subset of TeX used by _cv-content.tex to HTML."""

    #: macros taking no argument
    SIMPLE = {
        "eqc": "<sup>*</sup>",
        "advisee": "<sup>&#8224;</sup>",
        "today": None,          # filled in at construction
        "myname": None,
        "ldots": "&#8230;",
        ",": "&#8201;",         # \, thin space
        "&": "&amp;",
        "%": "%",
        "$": "$",
        "#": "#",
        "_": "_",
        "{": "{",
        "}": "}",
    }
    #: macros wrapping exactly one argument
    WRAP = {
        "textit": "<em>{}</em>",
        "emph": "<em>{}</em>",
        "textbf": "<strong>{}</strong>",
        "me": '<span custom-style="OwnName">{}</span>',
        "textsuperscript": "<sup>{}</sup>",
        "cvnote": "[{}]",
        "namefont": "{}",
        "mbox": "{}",
    }
    #: macros consumed for their effect on layout only
    IGNORE_NOARG = {"raggedright", "raggedleft", "centering", "normalfont",
                    "footnotesize", "small", "par", "noindent", "relax",
                    "vfill", "cvdatewwide", "cvdatew", "ignorespaces"}
    IGNORE_ONEARG = {"vspace", "hspace", "thispagestyle", "pagestyle", "label"}

    def __init__(self, defs: dict[str, str], today: _dt.date):
        self.defs = defs
        self.today = today
        self.simple = dict(self.SIMPLE)
        self.simple["today"] = f"{today:%B} {today.year}"
        self.simple["myname"] = html.escape(defs["myname"])
        for key in ("jabdc", "jabs", "jft", "jtamuga", "jutd"):
            self.simple[key] = self.convert(defs[key])

    # -- public ------------------------------------------------------------

    def convert(self, s: str) -> str:
        out: list[str] = []
        i = 0
        while i < len(s):
            c = s[i]
            if c == "\\":
                i = self._macro(s, i, out)
                continue
            if c == "{":
                body, i = read_group(s, i)
                out.append(self.convert(body))
                continue
            if c == "~":
                out.append("&#160;")
                i += 1
                continue
            if s.startswith("---", i):
                out.append("&#8212;")
                i += 3
                continue
            if s.startswith("--", i):
                out.append("&#8211;")
                i += 2
                continue
            if c in "\n\t":
                out.append(" ")
                i += 1
                continue
            out.append(html.escape(c, quote=False))
            i += 1
        return re.sub(r"  +", " ", "".join(out)).strip()

    # -- internals ---------------------------------------------------------

    def _macro(self, s: str, i: int, out: list[str]) -> int:
        m = re.match(r"\\([a-zA-Z]+|.)", s[i:], re.S)
        if not m:
            raise TexError(f"stray backslash at {s[i:i + 30]!r}")
        name = m.group(1)
        j = i + m.end()

        if name == "\\":                      # \\ -> hard line break
            out.append("<br />")
            return skip_ws(s, j)
        if name in (" ",):
            out.append(" ")
            return j
        if name == "href":
            url, j = read_group(s, skip_ws(s, j))
            text, j = read_group(s, skip_ws(s, j))
            out.append(f'<a href="{html.escape(self.plain(url), quote=True)}">'
                       f"{self.convert(text)}</a>")
            return j
        if name == "nth":
            arg, j = read_group(s, skip_ws(s, j))
            out.append(f"{self.plain(arg)}<sup>{ordinal_suffix(self.plain(arg))}</sup>")
            return j
        if name == "monthyeardate":
            return j                          # the \today that follows renders it
        if name in self.WRAP:
            arg, j = read_group(s, skip_ws(s, j))
            out.append(self.WRAP[name].format(self.convert(arg)))
            return j
        if name in self.IGNORE_ONEARG:
            _, j = read_group(s, skip_ws(s, j))
            return j
        if name in self.IGNORE_NOARG:
            return j
        if name in self.simple:
            out.append(self.simple[name])
            return j
        raise TexError(
            f"unknown macro \\{name} -- teach it to scripts/tex2html.py "
            f"(near {s[max(0, i - 40):i + 40]!r})")

    def plain(self, s: str) -> str:
        """Convert then strip tags; for attribute values and \\nth arguments."""
        return re.sub(r"<[^>]+>", "", self.convert(s))


# --------------------------------------------------------------------------
# block structure
# --------------------------------------------------------------------------

ENTRY = re.compile(r"\\(entl|entn|ent)(?![a-zA-Z])")

# Pandoc's docx writer ignores CSS, so anything that must survive into Word
# travels either as custom-style -- mapped to a paragraph style defined in
# reference.docx -- or as an inline text-align, which pandoc's HTML reader does
# read, but only on table cells.
# Right alignment rides on the cell's own style attribute. Two silent pandoc
# traps: a <col> style carrying both a width and a text-align parses as zero
# width (the column collapses to one character per line in Word), and align=
# on a <col> is ignored outright, so the alignment has to be on the cell.
RIGHT = "text-align: right;"


def styled(style: str, body: str) -> str:
    return f'<div custom-style="{style}"><p>{body}</p></div>\n'


def entry(body: str) -> str:
    """Entry text, hanging-indented in Word the way \\ent hangs in the PDF."""
    return styled("Entry", body).rstrip("\n")




class Renderer:
    def __init__(self, inline: Inline, defs: dict[str, str]):
        self.i = inline
        self.defs = defs

    def entries_block(self, body: str) -> str:
        items = []
        marks = list(ENTRY.finditer(body))
        if not marks:
            return ""
        if body[:marks[0].start()].strip():
            raise TexError(f"text before first entry: {body[:marks[0].start()]!r}")
        for n, m in enumerate(marks):
            end = marks[n + 1].start() if n + 1 < len(marks) else len(body)
            kind = m.group(1)
            rest = body[m.end():end]
            label = date = None
            if kind == "entl":
                label, k = read_group(rest, skip_ws(rest, 0))
                date, k = read_group(rest, skip_ws(rest, k))
            elif kind == "ent":
                date, k = read_group(rest, skip_ws(rest, 0))
            else:
                _, k = read_group(rest, skip_ws(rest, 0))
            text = self.i.convert(rest[k:])
            if label:
                text = f"<strong>{self.i.convert(label)}</strong>&#160;&#160;{text}"
            items.append((text, self.i.convert(date) if date else None))

        if not any(d for _, d in items):
            return "\n".join(entry(t) for t, _ in items) + "\n"

        rows = "\n".join(
            f"<tr><td>{entry(t)}</td>"
            f'<td style="{RIGHT}">{d or ""}</td></tr>'
            for t, d in items)
        return (
            '<table class="entries">\n'
            '<colgroup><col style="width: 84%;" />'
            '<col style="width: 16%;" /></colgroup>\n'
            f"<tbody>\n{rows}\n</tbody>\n</table>\n")

    def header_block(self, left: str, right: str) -> str:
        return (
            '<table class="hdr">\n'
            '<colgroup><col style="width: 58%;" />'
            '<col style="width: 42%;" /></colgroup>\n'
            f'<tbody>\n<tr><td>{self.i.convert(left)}</td>'
            f'<td style="{RIGHT}">{self.i.convert(right)}</td></tr>\n'
            "</tbody>\n</table>\n")

    def pub_heading(self, mode: str) -> str:
        marks = self.i.convert(self.defs["cvmarks"])
        head = "<h2>Publications</h2>\n"
        if mode == "full":
            return head + styled("Legend", marks)
        return f"<h2>Publications &#8212; {marks}</h2>\n"


def render(content: str, defs: dict[str, str], mode: str, today: _dt.date) -> str:
    inline = Inline(defs, today)
    r = Renderer(inline, defs)
    out: list[str] = []
    i = 0
    n = len(content)

    while i < n:
        m = re.compile(
            r"\\(begin|end|section\*|subsection\*|subsubsection\*|cvheader"
            r"|cvpubheading|newpage)(?![a-zA-Z])").search(content, i)
        if not m:
            trailing = inline.convert(content[i:])
            if trailing:
                out.append(f"<p>{trailing}</p>\n")
            break
        loose = inline.convert(content[i:m.start()])
        if loose:
            out.append(f"<p>{loose}</p>\n")
        cmd = m.group(1)
        j = m.end()

        if cmd == "newpage":
            out.append('<div class="page-break"></div>\n')
            i = j
        elif cmd == "cvpubheading":
            out.append(r.pub_heading(mode))
            i = j
        elif cmd == "cvheader":
            left, j = read_group(content, skip_ws(content, j))
            right, j = read_group(content, skip_ws(content, j))
            out.append(r.header_block(left, right))
            i = j
        elif cmd.startswith("section") or cmd.startswith("subsection") \
                or cmd.startswith("subsubsection"):
            level = {"section*": 2, "subsection*": 3, "subsubsection*": 4}[cmd]
            title, j = read_group(content, skip_ws(content, j))
            out.append(f"<h{level}>{inline.convert(title)}</h{level}>\n")
            i = j
        elif cmd == "begin":
            env, j = read_group(content, skip_ws(content, j))
            close = content.index(f"\\end{{{env}}}", j)
            if env == "entries":
                _, j = read_optional(content, j)
                out.append(r.entries_block(content[j:close]))
            elif env == "center":
                inner = content[j:close]
                body = inline.convert(inner)
                if "\\namefont" in inner:
                    out.append(f"<h1>{body}</h1>\n")   # Heading 1 centres it
                else:
                    out.append(styled("Centered", body))
            else:
                raise TexError(f"unknown environment: {env}")
            i = close + len(f"\\end{{{env}}}")
        else:  # a stray \end
            raise TexError(f"unexpected \\{cmd} at offset {m.start()}")

    return "".join(out)


CSS = """\
body { font-family: "EB Garamond", Garamond, Georgia, "Times New Roman", serif; }
h1 {
  font-family: "EB Garamond", Garamond, Georgia, "Times New Roman", serif;
  text-align: center;
}
h2, h3, h4 {
  font-family: "Alegreya Sans", "Trebuchet MS", Arial, sans-serif;
}
h1, h2, h3 { font-weight: 700; }
h4 { font-style: italic; font-weight: 500; }
span[custom-style="OwnName"] { font-weight: 600; }
table { width: 100%; border-collapse: collapse; }
td { vertical-align: top; border: none; }
td[style*="right"] { text-align: right; }
div[custom-style="Entry"] p { padding-left: 0.5in; text-indent: -0.5in; }
div[custom-style="Centered"] { text-align: center; }
div[custom-style="Legend"] { font-size: 90%; }
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", required=True, choices=MODES)
    ap.add_argument("--content", default=ROOT / "_cv-content.tex", type=Path)
    ap.add_argument("--preamble", default=ROOT / "_cv-preamble.tex", type=Path)
    ap.add_argument("--date", help="YYYY-MM-DD; defaults to today")
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args()

    today = (_dt.date.fromisoformat(args.date) if args.date
             else _dt.date.today())

    try:
        defs = load_preamble_defs(strip_comments(args.preamble.read_text()))
        content = resolve_conditionals(
            strip_comments(args.content.read_text()), args.mode)
        body = render(content, defs, args.mode, today)
    except TexError as exc:
        print(f"tex2html: {exc}", file=sys.stderr)
        return 1

    title = html.escape(defs["myname"])
    doc = (f'<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8" />\n'
           f"<title>{title}: Curriculum Vitae</title>\n<style>\n{CSS}</style>\n"
           f"</head>\n<body>\n{body}</body>\n</html>\n")

    if args.output:
        args.output.write_text(doc)
    else:
        sys.stdout.write(doc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
