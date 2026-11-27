"""Repair spaces introduced by rich-text editors in Python examples."""
import ast
import io
import re
import tokenize

from bs4 import Comment, NavigableString


NBSP = "\u00a0"
PYTHON_LINE = re.compile(
    r"^\s*(?:def\s+|from\s+\S+\s+import|import\s+|class\s+|if\s+|for\s+\w+\s+in\s+|print\s*\()",
    re.MULTILINE,
)


def _parts(tag, line_spans=False):
    """Keep references to the original text nodes, with the same line breaks as codeText in js/blog.js."""
    for child in tag.children:
        if isinstance(child, NavigableString):
            if not isinstance(child, Comment):
                yield child
        elif child.name == "br":
            if not line_spans:
                yield "\n"
        elif line_spans or "linenum" not in child.get("class", ()):
            yield from _parts(child, line_spans)


def repair_python_spaces(block):
    if NBSP not in block.get_text():
        return
    code = block.find("code")
    classes = set(block.get("class", ())) | set(code.get("class", ()) if code else ())
    languages = {name.lower().removeprefix("language-").removeprefix("lang-") for name in classes}
    is_python = bool(languages & {"python", "py", "python3"})
    labelled = any(name.startswith(("language-", "lang-")) for name in classes) or ("hljs" in classes and len(classes) > 1)
    if labelled and not is_python:
        return

    lines = block.select(".line")
    numbered = block.select_one("ol.linenums")
    groups = lines or (numbered.find_all(recursive=False) if numbered else [block])
    parts = []
    for index, group in enumerate(groups):
        if index:
            parts.append("\n")
        parts.extend(_parts(group, bool(lines)))
    original = "".join(parts)
    plain = original.replace(NBSP, " ")
    if not is_python and not PYTHON_LINE.search(plain):
        return

    # Token coordinates refer to the space-normalized copy. Keep the original
    # text of string literals and comments, including those spanning HTML nodes.
    line_starts = [0] + [match.end() for match in re.finditer("\n", plain)]
    repaired = list(plain)
    try:
        if not is_python:
            ast.parse(plain)
        for tok in tokenize.generate_tokens(io.StringIO(plain).readline):
            if tokenize.tok_name[tok.type] in {"STRING", "COMMENT", "FSTRING_MIDDLE", "TSTRING_MIDDLE"}:
                start = line_starts[tok.start[0] - 1] + tok.start[1]
                end = line_starts[tok.end[0] - 1] + tok.end[1]
                repaired[start:end] = original[start:end]
            elif tok.type == tokenize.ERRORTOKEN:
                return
    except (SyntaxError, tokenize.TokenError):
        return

    offset = 0
    for part in parts:
        end = offset + len(part)
        if isinstance(part, NavigableString) and NBSP in part:
            value = "".join(repaired[offset:end])
            if value != part:
                part.replace_with(value)
        offset = end
