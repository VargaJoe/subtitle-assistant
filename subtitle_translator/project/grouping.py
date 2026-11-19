"""Whole translation units and markup diagnostics; no model calls or timing edits."""

from html.parser import HTMLParser
import hashlib
import json
import re

from .errors import ProjectError

TAGS = {"i", "b", "u", "font"}
MARKERS = re.compile(r"(?m)^\s*[-–—•]\s*")


class Markup(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.errors = []
        self.plain = ""
        self.runs = []

    def handle_starttag(self, tag, attrs):
        if tag not in TAGS:
            self.errors.append(f"Unsupported formatting tag: {tag}")
            return
        self.stack.append((tag, tuple(sorted((k, v or "") for k, v in attrs))))

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1][0] != tag:
            self.errors.append(f"Unmatched or misnested closing tag: {tag}")
            return
        self.stack.pop()

    def handle_startendtag(self, tag, attrs):
        self.errors.append(f"Unsupported self-closing tag: {tag}")

    def handle_comment(self, data):
        self.errors.append("HTML comments are not subtitle formatting")

    def handle_data(self, data):
        start = len(self.plain)
        self.plain += data
        if data:
            self.runs.append({"start": start, "end": len(self.plain),
                              "styles": list(self.stack)})


def profiles(texts):
    parser = Markup()
    result = []
    for text in texts:
        parser.plain, parser.runs = "", []
        before = len(parser.errors)
        parser.feed(text)
        # Flush bare ampersands/incomplete entities before taking this cue's
        # snapshot. HTMLParser otherwise buffers them into the next cue. Its
        # close() flushes lexical input but retains our document-level tag stack.
        parser.close()
        result.append({"plain": parser.plain, "runs": parser.runs[:],
                       "open_after": list(parser.stack), "errors": parser.errors[before:]})
    if parser.stack and result:
        result[-1]["errors"].append("Unclosed formatting at end of document")
    return result


def _signatures(profile):
    return {_style_key(style) for run in profile["runs"] if profile["plain"][run["start"]:run["end"]].strip()
            for style in run["styles"]}


def _style_key(style):
    return (style[0], tuple(tuple(attribute) for attribute in style[1]))


def _uniform_styles(profile):
    visible = [{_style_key(style) for style in run["styles"]} for run in profile["runs"]
               if profile["plain"][run["start"]:run["end"]].strip()]
    return set.intersection(*visible) if visible else set()


def _complete(text):
    text = text.strip()
    if not text:
        return True
    if ((text.startswith("(") and text.endswith(")")) or
            (text.startswith("[") and text.endswith("]")) or "♪" in text or "♫" in text):
        return True
    if len(MARKERS.findall(text)) > 1:
        return True
    if len(text) > 3 and text.isupper() and any(word in text for word in ("MUSIC", "SOUND", "DOOR", "PHONE", "NOISE", "ALARM")):
        return True
    return text.rstrip('"\'”’)]').endswith((".", "!", "?", "…"))


def translation_units(project_id, entries):
    info = profiles([entry["source_text"] for entry in entries])
    groups, current, reasons = [], [], set()
    for index, entry in enumerate(entries):
        current.append(index)
        next_info = info[index + 1] if index + 1 < len(entries) else None
        join = False
        if next_info is not None:
            if info[index]["open_after"]:
                join = True
                reasons.add("formatting_scope")
            elif not _complete(info[index]["plain"]):
                next_text = next_info["plain"].strip()
                gap = entries[index + 1]["start_ms"] - entry["end_ms"]
                if (gap <= 2000 and next_text and not MARKERS.match(next_text)
                        and not next_text.startswith(("[", "(")) and not (len(next_text) > 3 and next_text.isupper())):
                    join = True
                    reasons.add("sentence_continuation")
        if not join:
            groups.append((current, sorted(reasons)))
            current, reasons = [], set()
    units = []
    for group, reasons in groups:
        members = [dict(entries[i]) for i in group]
        signature = [(e["entry_id"], e["source_revision"], e["timing_revision"]) for e in members]
        unit_id = "unit_" + hashlib.sha256(json.dumps([project_id, signature]).encode()).hexdigest()[:24]
        member_profiles = [info[i] for i in group]
        units.append({"unit_id": unit_id, "entry_ids": [e["entry_id"] for e in members],
                      "source_entries": members, "source_text": " ".join(p["plain"].strip() for p in member_profiles),
                      "formatting": member_profiles, "group_reasons": reasons})
    return units


def validate_mapping(unit, mapped):
    """Validate shape/formatting/voice markers; semantic alignment still needs review."""
    by_id = {item["entry_id"]: item for item in mapped}
    source = unit["source_entries"]
    # Protected/nonwritable entries remain part of the semantic unit as fixed context.
    target_texts = [by_id[e["entry_id"]]["text"] if e["entry_id"] in by_id
                    else e.get("target_text") or e["source_text"] for e in source]
    target_profiles = profiles(target_texts)
    errors = [message for p in target_profiles for message in p["errors"]]
    if errors:
        raise ProjectError("invalid_translation_formatting", "Target formatting is unbalanced or unsupported", {"issues": errors})
    source_profiles = unit["formatting"]
    all_source = set().union(*(_signatures(p) for p in source_profiles))
    all_target = set().union(*(_signatures(p) for p in target_profiles))
    if all_source != all_target:
        raise ProjectError("formatting_scope_changed", "Target formatting styles/attributes differ from source")
    for original, expected, actual in zip(source, source_profiles, target_profiles):
        if original["entry_id"] not in by_id:
            continue
        if not _uniform_styles(expected).issubset(_uniform_styles(actual)):
            raise ProjectError("formatting_scope_changed", "Full-cue source formatting was not retained", {"entry_id": original["entry_id"]})
        # Partial source emphasis cannot be widened to the whole target unit/cue.
        if _signatures(expected) - _uniform_styles(expected) and _uniform_styles(actual) - _uniform_styles(expected):
            raise ProjectError("formatting_scope_changed", "Partial emphasis was expanded to the whole cue", {"entry_id": original["entry_id"]})
        if len(MARKERS.findall(expected["plain"])) != len(MARKERS.findall(actual["plain"])):
            raise ProjectError("speaker_markers_changed", "Dialogue speaker markers must remain attached to their cue", {"entry_id": original["entry_id"]})
        for pattern in (r"\[[^\]]*\]", r"[♪♫]"):
            if len(re.findall(pattern, expected["plain"])) != len(re.findall(pattern, actual["plain"])):
                raise ProjectError("accessibility_markers_changed", "Accessibility/music markers were lost or added", {"entry_id": original["entry_id"]})
    return [{"code": "partial_formatting_review", "entry_id": e["entry_id"]}
            for e, p in zip(source, source_profiles) if _signatures(p) - _uniform_styles(p)]
