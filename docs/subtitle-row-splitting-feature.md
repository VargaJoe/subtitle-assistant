# Subtitle Row Splitting Feature

- Added configurable subtitle row splitting for SRT output.
- New config options in config.yaml and Config dataclass:
  - max_row_length (default: 42, recommended for SRT)
  - row_split_method ("even", "word", "char"; default: "even")
- Splitting logic implemented in srt_parser.py:
  - "even": splits lines as evenly as possible, tries not to break words
  - "word": splits only at word boundaries
  - "char": splits at exact character count, may break words
- SRT output now applies user-configured splitting for each subtitle entry.
- No changes to translation logic or AI model input/output.
- Improves compatibility with subtitle viewers that do not wrap long lines.
- All changes tested and validated; no errors found.
