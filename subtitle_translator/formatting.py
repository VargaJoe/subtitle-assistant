"""Dependency-free display-row wrapping, separate from source serialization.

Wrapping never moves text between subtitle cues. Existing physical lines remain
boundaries, including dialogue/speaker lines. Well-nested inline HTML keeps its
original scope: an active tag is closed/reopened only at a new display row.
"""

from bisect import bisect_left
from dataclasses import dataclass
from html import unescape
import re
from typing import Iterable, Optional


_TOKEN = re.compile(
    r"<!--[\s\S]*?-->|<[A-Za-z/!?](?:\"[^\"]*\"|'[^']*'|[^'\">])*>"
    r"|&(?:#[0-9]+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]+);|.",
    re.DOTALL,
)
_TAG = re.compile(r"<\s*(/?)\s*([A-Za-z][A-Za-z0-9:-]*)(?=[\s/>])")
_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
})


@dataclass(frozen=True)
class _Atom:
    raw: str
    width: int
    space: bool = False


def _tokens(paragraph, normalize_spaces):
    result = []
    have_text = previous_space = False
    for match in _TOKEN.finditer(paragraph):
        raw = match.group()
        if raw.startswith("<") and len(raw) > 1:
            result.append(_Atom(raw, 0))
            continue
        space = len(raw) == 1 and raw.isspace()
        if normalize_spaces and space:
            if not have_text or previous_space:
                continue
            raw = " "
        width = len(unescape(raw)) if raw.startswith("&") else len(raw)
        result.append(_Atom(raw, width, space))
        have_text = True
        previous_space = space
    if normalize_spaces:
        # Trim visible trailing whitespace without discarding following tags.
        for index in range(len(result) - 1, -1, -1):
            if result[index].width:
                if not result[index].space:
                    break
                del result[index]
    return result


def _word_ranges(tokens, max_length, method, target_line_count):
    words, start, width = [], 0, 0
    for index, token in enumerate(tokens):
        if token.space:
            words.append((start, index, width))
            start, width = index + 1, 0
        else:
            width += token.width
    words.append((start, len(tokens), width))
    if len(words) == 1:
        return [(0, len(tokens))]

    prefix = [0]
    for _, _, word_width in words:
        prefix.append(prefix[-1] + word_width + 1)

    def length(left, right):
        return prefix[right] - prefix[left] - 1

    row_words = []
    if (method == "even" and target_line_count and target_line_count > 1
            and length(0, len(words)) > max_length):
        # Historical explicit row-count hints are a soft width preference. A
        # source with several physical lines never enters this branch.
        remaining = min(int(target_line_count), len(words))
        left = 0
        while remaining > 1:
            last = len(words) - remaining + 1
            desired = prefix[left] + (length(left, len(words)) - remaining + 1) / remaining + 1
            split = bisect_left(prefix, desired, left + 1, last + 1)
            candidates = {max(left + 1, min(last, split)), max(left + 1, min(last, split - 1))}
            right = min(candidates, key=lambda end: (abs(prefix[end] - desired), end))
            row_words.append((left, right))
            left, remaining = right, remaining - 1
        row_words.append((left, len(words)))
    elif method == "even" and length(0, len(words)) > max_length:
        candidates = [
            right for right in range(1, len(words))
            if length(0, right) <= max_length and length(right, len(words)) <= max_length
        ]
        if candidates:
            right = min(candidates, key=lambda end: abs(length(0, end) - length(end, len(words))))
            row_words = [(0, right), (right, len(words))]
    if not row_words:
        left = 0
        for right in range(1, len(words)):
            if length(left, right + 1) > max_length:
                row_words.append((left, right))
                left = right
        row_words.append((left, len(words)))
    return [(words[left][0], words[right - 1][1]) for left, right in row_words]


def _char_ranges(tokens, max_length):
    result, start, width = [], 0, 0
    for index, token in enumerate(tokens):
        if token.width and width and width + token.width > max_length:
            result.append((start, index))
            start, width = index, 0
        width += token.width
    result.append((start, len(tokens)))
    return result


def _update_scope(raw, scope):
    tag = _TAG.match(raw)
    if not tag:
        return
    closing, name = tag.groups()
    if closing:
        for index in range(len(scope) - 1, -1, -1):
            if scope[index][0].lower() == name.lower():
                del scope[index:]
                break
    elif name.lower() not in _VOID_TAGS and not raw.rstrip().endswith("/>"):
        scope.append((name, raw))


def _render_rows(tokens, ranges, scope):
    rows = []
    for start, end in ranges:
        parts = [opening for _, opening in scope]
        for token in tokens[start:end]:
            parts.append(token.raw)
            if token.width == 0:
                _update_scope(token.raw, scope)
        parts.extend(f"</{name}>" for name, _ in reversed(scope))
        rows.append("".join(parts))
    return rows


def format_subtitle_texts(
    texts: Iterable[str], max_length: int = 42, method: str = "even",
    target_line_count: Optional[int] = None,
    *, target_line_counts: Optional[Iterable[Optional[int]]] = None,
) -> list[str]:
    """Wrap cue texts in source order, carrying inline HTML scope across cues.

    Returns one string per supplied cue. IDs/timestamps remain the caller's
    responsibility and no visible text is transferred between cues. Each output
    row is independently balanced for well-nested input, including a tag opened
    in an earlier cue. HTML entities are indivisible and count by decoded length.
    ``word``/``even`` retain unbreakable words even when they exceed the width.

    Unknown/unmatched closing tags are retained verbatim; no opening scope is
    invented. Unclosed openings carry to following cues. Misnested closes retain
    their literal source tag and end the matching and nested tracked scopes;
    this formatter does not validate or repair malformed markup. Source/original
    archival export must bypass display formatting entirely.

    ``target_line_counts`` supplies optional legacy row-count hints per cue,
    overriding the shared ``target_line_count``. Its length must match ``texts``.
    """
    texts = list(texts)
    hints = ([target_line_count] * len(texts) if target_line_counts is None else
             list(target_line_counts))
    if len(hints) != len(texts):
        raise ValueError("target_line_counts must contain exactly one hint per cue")
    if max_length < 1:
        return texts
    result, scope = [], []
    method = method if method in {"word", "char"} else "even"
    for text, cue_hint in zip(texts, hints):
        paragraphs = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        rows = []
        for paragraph in paragraphs:
            if not paragraph.strip():
                rows.append("")
                continue
            tokens = _tokens(paragraph.strip(), normalize_spaces=method != "char")
            hint = cue_hint if len(paragraphs) == 1 else None
            ranges = (_char_ranges(tokens, max_length) if method == "char" else
                      _word_ranges(tokens, max_length, method, hint))
            rows.extend(_render_rows(tokens, ranges, scope))
        result.append("\n".join(rows))
    return result


def split_subtitle_text(
    text: str, max_length: int = 42, method: str = "even",
    target_line_count: Optional[int] = None,
) -> str:
    """Wrap one cue; keep the historical legacy/standalone call signature.

    ``target_line_count > 1`` is an optional legacy hint on a single input line
    in ``even`` mode; it can exceed ``max_length`` to approach the requested row
    count. Use the default for width-limited display wrapping, and use
    :func:`format_subtitle_texts` when formatting may span cue boundaries.
    """
    if not text or max_length < 1:
        return text
    return format_subtitle_texts([text], max_length, method, target_line_count)[0]
