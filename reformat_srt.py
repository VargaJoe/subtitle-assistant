#!/usr/bin/env python3
"""Lightweight SRT display reformatter; no model or YAML dependency at import."""

import argparse
import os
from pathlib import Path
import sys
import tempfile

from subtitle_translator.formatting import format_subtitle_texts, split_subtitle_text
from subtitle_translator.project.errors import ProjectError
from subtitle_translator.project.srt import parse_source


def parse_srt_file(file_path: Path, max_row_length: int = 42, row_split_method: str = "even"):
    """Validate the entire file before atomically replacing its display rows.

    Invalid/undecodable input returns False and leaves the input bytes intact.
    Cue IDs and timing lines are copied verbatim; inline styles can continue
    between cues. This historical standalone command deliberately edits the
    supplied file, so callers should pass a working copy, not an original.
    """
    file_path = Path(file_path)
    temporary_path = None
    try:
        raw = file_path.read_bytes()
        parsed = parse_source(raw)
        if parsed.errors:
            first = parsed.errors[0]
            print(f"Cannot reformat {file_path}: {first.code} at line {first.line}: {first.message}")
            return False
        content = raw.decode(parsed.encoding).lstrip("\ufeff")
        lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        formatted = format_subtitle_texts(
            (entry.text for entry in parsed.entries), max_row_length, row_split_method,
        )
        blocks = [
            f"{lines[entry.source_line - 1]}\n{lines[entry.source_line]}\n{text}"
            for entry, text in zip(parsed.entries, formatted)
        ]
        newline = {"CRLF": "\r\n", "CR": "\r"}.get(parsed.newline, "\n")
        output = ("\n\n".join(blocks) + "\n").replace("\n", newline).encode("utf-8")
        if raw.startswith(b"\xef\xbb\xbf"):
            output = b"\xef\xbb\xbf" + output
        with tempfile.NamedTemporaryFile(mode="wb", dir=file_path.parent, prefix=f".{file_path.name}.", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(output)
        os.replace(temporary_path, file_path)
        return True
    except (OSError, UnicodeError, ProjectError) as exc:
        print(f"Cannot reformat {file_path}: {exc}")
        return False
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def load_config():
    """Read optional YAML configuration only when the standalone CLI needs it."""
    config_path = Path("config.yaml")
    if config_path.exists():
        try:
            import yaml

            with config_path.open("r", encoding="utf-8") as source:
                config = yaml.safe_load(source) or {}
            output_config = config.get("output", {})
            return {
                "max_row_length": output_config.get("max_row_length", 42),
                "row_split_method": output_config.get("row_split_method", "even"),
            }
        except Exception as exc:
            print(f"Failed to load optional config.yaml: {exc}")
    return {"max_row_length": 42, "row_split_method": "even"}


def main():
    parser = argparse.ArgumentParser(description="Fast SRT reformatter - splits subtitle lines")
    parser.add_argument("files", nargs="+", help="Working-copy SRT files to reformat in place")
    parser.add_argument("--max-length", type=int, help="Maximum line length (overrides config)")
    parser.add_argument("--method", choices=["even", "word", "char"], help="Split method (overrides config)")
    args = parser.parse_args()
    config = load_config()
    max_length = args.max_length if args.max_length is not None else config["max_row_length"]
    method = args.method or config["row_split_method"]
    if not isinstance(max_length, int) or isinstance(max_length, bool) or max_length < 1:
        parser.error("maximum line length must be a positive integer")
    if method not in {"even", "word", "char"}:
        parser.error("split method must be even, word or char")
    print(f"SRT Reformatter - Max length: {max_length}, Method: {method}")
    success_count = error_count = 0
    for file_arg in args.files:
        file_path = Path(file_arg)
        if parse_srt_file(file_path, max_length, method):
            print(f"Success: {file_path.name}")
            success_count += 1
        else:
            error_count += 1
    print(f"Results: {success_count} success, {error_count} failed")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
