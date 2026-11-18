# Subtitle Assistant — repository entry points

The owner's Mission Control memory and identity instructions remain in force.
The subtitle tool itself uses local project storage and has no Obsidian/MC dependency.

For subtitle translation, inspection or editing, read
[the Subtitle Assistant skill](skills/subtitle-assistant/SKILL.md) and use the
shared tool. Keep timed cue identities and manual corrections intact:

```powershell
python -S -m subtitle_translator.tool capabilities --json
python -S -m subtitle_translator.tool doctor --json
```

Read [the v1 contract](docs/tool-v1-contract.md) for the available commands and
error/receipt semantics, and [the development plan](docs/tool-first-development-plan.md)
for milestone scope. Use an explicit absolute `--workspace` when running outside
the repository. The current tool supports grouped external-agent translation,
manual edits/history, job activity/control and source/original/target/draft exports
through JSON CLI and loopback HTTP. The supervised browser GUI has an M7a preview;
see [GUI usage and persistence](docs/gui-preview.md). Provider OAuth remains later work.
The app skill/API require no MCP registration. Do not rely on unavailable
`read_graph` or `add_observation` tools as prerequisites for using this local tool.

Preserve the original subtitle and owner data. Use new output paths; inspect
diagnostics and request receipts instead of replaying uncertain writes with a new ID.
Personal pilot files and outputs stay under ignored workspace directories.

Focused model-free checks:

```powershell
python -S -m unittest discover -s tests/tool -q
```

Preserve pre-existing unrelated changes. Stage individual files only. The owner
retains approval/merge authority for `develop`.
