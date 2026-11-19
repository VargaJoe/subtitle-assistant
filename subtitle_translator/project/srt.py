"""Strict source import with diagnostics, separate from legacy tolerant parsing.

The original bytes are archived; working text only normalizes newline characters.
Unlike the legacy translation formatter, source export never reflows text or tags.
"""

from dataclasses import asdict, dataclass
import hashlib
import re

from ..srt_format import format_timestamp
from .errors import ProjectError

MAX_INTEGER = (1 << 63) - 1

TIMING = re.compile(
    r"(?P<sh>\d{2,}):(?P<sm>\d{2}):(?P<ss>\d{2}),(?P<sf>\d{3})"
    r"[ \t]*-->[ \t]*"
    r"(?P<eh>\d{2,}):(?P<em>\d{2}):(?P<es>\d{2}),(?P<ef>\d{3})"
)


@dataclass(frozen=True)
class SourceEntry:
    ordinal: int
    source_index: int
    start_ms: int
    end_ms: int
    text: str
    source_line: int


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    block: int
    line: int
    message: str

    def to_dict(self):
        return asdict(self)


@dataclass
class ParsedSource:
    raw: bytes
    encoding: str
    newline: str
    entries: list
    diagnostics: list
    block_count: int

    @property
    def sha256(self):
        return hashlib.sha256(self.raw).hexdigest()

    @property
    def errors(self):
        return [d for d in self.diagnostics if d.severity == "error"]

    def report(self):
        return {
            "source_sha256": self.sha256,
            "byte_count": len(self.raw),
            "encoding": self.encoding,
            "newline": self.newline,
            "block_count": self.block_count,
            "entry_count": len(self.entries),
            "error_count": len(self.errors),
            "warning_count": len(self.diagnostics) - len(self.errors),
            "diagnostics": [d.to_dict() for d in self.diagnostics[:100]],
            "diagnostics_truncated": len(self.diagnostics) > 100,
        }


def parse_source(raw: bytes, encoding=None) -> ParsedSource:
    chosen = encoding or ("utf-8-sig" if raw.startswith(b"\xef\xbb\xbf") else "utf-8")
    try:
        content = raw.decode(chosen)
    except (UnicodeError, LookupError) as exc:
        raise ProjectError(
            "source_encoding_error",
            "Cannot decode the subtitle. Supply its encoding explicitly; no lossy fallback is used.",
            {"encoding": chosen},
        ) from exc
    if content.startswith("\ufeff"):
        content = content[1:]
    crlf = content.count("\r\n")
    lone_cr = content.count("\r") - crlf
    lone_lf = content.count("\n") - crlf
    kinds = sum(bool(n) for n in (crlf, lone_cr, lone_lf))
    newline = "mixed" if kinds > 1 else "CRLF" if crlf else "CR" if lone_cr else "LF"
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    entries, diagnostics, seen = [], [], set()
    block_lines, line_number, block_start = [], 0, 1
    blocks = []
    for line_number, line in enumerate(content.split("\n"), 1):
        if not line.strip():
            if block_lines:
                blocks.append((block_start, block_lines))
                block_lines = []
        else:
            if not block_lines:
                block_start = line_number
            block_lines.append(line)
    if block_lines:
        blocks.append((block_start, block_lines))

    for ordinal, (start_line, lines) in enumerate(blocks, 1):
        def issue(code, severity, message, offset=0):
            diagnostics.append(Diagnostic(code, severity, ordinal, start_line + offset, message))

        if len(lines) < 3:
            issue("invalid_block", "error", "A block needs an index, a timestamp and text")
            continue
        index_text = lines[0].strip()
        normalized_index = index_text.lstrip("0") or "0"
        if not re.fullmatch(r"[0-9]+", index_text) or normalized_index == "0":
            issue("invalid_index", "error", "Subtitle index must be a positive integer")
            continue
        if len(normalized_index) > 19 or int(normalized_index) > MAX_INTEGER:
            issue("index_out_of_range", "error", "Subtitle index exceeds the supported 64-bit integer range")
            continue
        source_index = int(normalized_index)
        match = TIMING.fullmatch(lines[1].strip())
        if not match:
            issue("invalid_timestamp", "error", "Timestamp must use HH:MM:SS,mmm --> HH:MM:SS,mmm", 1)
            continue
        groups = match.groupdict()
        if any(len(groups[key].lstrip("0")) > 13 for key in ("sh", "eh")):
            issue("timestamp_out_of_range", "error", "Timestamp exceeds the supported 64-bit millisecond range", 1)
            continue
        values = {key: int(value.lstrip("0") or "0") for key, value in groups.items()}
        if any(values[key] >= 60 for key in ("sm", "ss", "em", "es")):
            issue("invalid_timestamp", "error", "Minutes and seconds must be below 60", 1)
            continue
        start_ms = ((values["sh"] * 60 + values["sm"]) * 60 + values["ss"]) * 1000 + values["sf"]
        end_ms = ((values["eh"] * 60 + values["em"]) * 60 + values["es"]) * 1000 + values["ef"]
        if start_ms > MAX_INTEGER or end_ms > MAX_INTEGER:
            issue("timestamp_out_of_range", "error", "Timestamp exceeds the supported 64-bit millisecond range", 1)
            continue
        if end_ms <= start_ms:
            issue("invalid_duration", "error", "End time must be later than start time", 1)
            continue
        embedded_cue = next((offset for offset in range(2, len(lines) - 1)
                             if re.fullmatch(r"[0-9]+", lines[offset].strip())
                             and "-->" in lines[offset + 1]
                             and re.match(r"[0-9]+:[0-9]", lines[offset + 1].lstrip())), None)
        if embedded_cue is not None:
            issue("missing_separator", "error", "A second subtitle cue needs a blank separator", embedded_cue)
            continue
        text = "\n".join(lines[2:])
        if source_index in seen:
            issue("duplicate_index", "warning", "Duplicate SRT index retained as a separate entry")
        seen.add(source_index)
        if entries and start_ms < entries[-1].start_ms:
            issue("out_of_order_time", "warning", "Source order is retained despite decreasing start time", 1)
        entries.append(SourceEntry(ordinal, source_index, start_ms, end_ms, text, start_line))
    if not entries:
        diagnostics.append(Diagnostic("no_entries", "error", 0, 1, "No valid subtitle entries found"))
    return ParsedSource(raw, chosen, newline, entries, diagnostics, len(blocks))


def render_source(entries) -> bytes:
    """Canonical UTF-8/LF source export; preserve text, tags, indices and times."""
    blocks = [
        f"{entry['source_index']}\n"
        f"{format_timestamp(entry['start_ms'])} --> {format_timestamp(entry['end_ms'])}\n"
        f"{entry['source_text']}"
        for entry in entries
    ]
    return ("\n\n".join(blocks) + "\n").encode("utf-8")
