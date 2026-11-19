# Tool and supervised GUI preview — review handoff

Verified locally on Windows, 2026-11-19. This change packages the M0/M1/M2 tool
and the working M7a GUI preview. Full supervised-edit and video/language
acceptance remain open; it does not complete the later context/OAuth milestones.

## Review and cleanup

- Kept the earlier persistent legacy quota tracking. Fixed waiting across
  simultaneous minute/hour/day quotas and weighted usage; recheck after sleeping
  before permitting a request, within one total `max_wait` budget.
- Kept virtual-environment selection and direct native PowerShell launching.
  Removed embedded argument quotes that made input/output paths invalid under
  modern native argument passing. Native tests cover spaces and quota-stop exit 103.
- Reconciled an already-published pending export from its saved receipt/hash even
  after later source, target or timing edits. Missing/changed output retains
  revision and no-clobber checks.
- Matched the capabilities schema to the implemented GUI and draft export.
  Added optional formal contract checks and Linux/Windows CI without model access.

Personal subtitles, translation text, SQLite workspaces, credentials and runtime
evidence remain in ignored local directories. Repository fixtures are synthetic.

## Validation

```powershell
python -S -m unittest discover -s tests/tool -q
node --test tests/web/test_editor_state.mjs
node --check subtitle_translator/web/app.js
```

Results: **142 tool tests**, **16 editor-state tests**, syntax check passed.
The Windows tool run includes three real PowerShell child-process tests. Those
tests are explicitly skipped on other operating systems.

The affected legacy checks passed with the existing optional environment:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_api_batch_cross_entry.py tests/unit/test_multiline_fix.py tests/integration/test_backend_switching.py -q -o addopts=
```

Result: **23 passed**, with three third-party deprecation warnings.

Formal contracts use a separate optional extra:

```powershell
python -m pip install '.[contracts]'
python -m unittest discover -s tests/contracts -q
```

Result: **3 passed**: standard JSON Schema/OpenAPI validation with local relative
references, runtime capabilities, and both entry-list and edit-result snapshots
including a persisted partial translation.

A wheel installed into a fresh virtual environment was exercised with isolated
imports outside checkout resolution. CLI import/draft export and all four GUI
assets served over real local HTTP passed without model dependencies.

## Manual acceptance still to perform

```powershell
.\Start-SubtitleAssistant.cmd
```

1. In a test project, save partial target wording without marking it reviewed;
   reopen the same workspace and verify it remains saved.
2. Request the draft download. Cancel once, then confirm; inspect visible review
   markers, source fallbacks and the timestamped review list alongside the video.
3. During agent work, edit target, source and timing; verify protections, conflicts,
   live status and the resulting export. This is the remaining full M7a acceptance.

The separate editor opening is recorded as a later, low-priority UX refinement in
[the task tracker](implementation-tasks.md). Automated browser visual acceptance
has not been performed; no live pilot data was changed for test convenience.
