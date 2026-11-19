---
name: subtitle-assistant
description: Translate, inspect and edit SRT subtitles through Subtitle Assistant's persistent local tool, preserving timed cues, formatting and manual corrections.
---

Use the repository's model-free tool for subtitle work. Supply translations with
your own model; the application needs no model login, MCP registration or cloud key.
Run from the repository root, or use the installed `subtitle-assistant` command.

```powershell
python -S -m subtitle_translator.tool doctor --workspace <absolute-workspace> --json
python -S -m subtitle_translator.tool capabilities --workspace <absolute-workspace> --json
```

For command examples, request fields and the local API, read
[the tool workflow](../../docs/agent-tool-workflow.md). JSON errors identify the
specific problem. A stopped API permits direct CLI use; a data/revision error
requires reconciliation through the tool, not database or SRT patching.

Import into an explicit workspace, prepare a batch at the current revision,
translate its complete units, submit keyed results, validate and export to a new
target path. Save exact mutation requests with UUIDs before sending. After an
uncertain result, inspect its receipt or replay the identical request; changing
payload under the same UUID is a conflict.

Three boundaries matter:

- A display row is not a timed cue or translation unit. Read each unit and its
  source/target context together; some sentences and tag scopes span cues.
- Return every `writable_entry_id` once, nested under its `unit_id`. Translate
  naturally as a group, then align the meaning to each original start/stop cue.
  Preserve speaker markers and semantic emphasis. Never proportionally slice
  translated characters, pad missing entries, or invent timestamps.
- Context and protected targets are read-only for a translation submission.
  Preserve manual corrections; source/timing edits invalidate prepared work.
  Fetch current state and prepare again after a revision conflict.

Only mark a translation `agent_reviewed` after reviewing wording, cue alignment,
names and formatting against the available context. If uncertain, submit
`needs_review`/`unchecked` and report it. The tool checks structure and anchors;
it cannot prove semantic timing or identify speakers from text alone. Do not
invent plot or character facts. Persistent story/glossary support is later work.

Report `job.activity` at meaningful phases. Before preparing or submitting, check
`job.status`: acknowledge `pause_requested` with phase `paused` and wait for an
explicit resume; do not submit when paused/cancelled. Freshness expires without a
heartbeat, independently of saved translation progress. Actor labels are metadata,
not authentication or permission.
Use `batch_id` only while that batch is prepared; after submission, report
project-level validating/finished activity without the closed batch ID.

Save partial work as `draft`/`unchecked`; review is separate from persistence.
Finish with validation, issues and paths to the result. Use `target` for a fully
reviewed final export. For video testing of unfinished work, explicitly request
the `draft` variant: pending cues are visibly marked and missing targets use
marked source text. Its receipt includes the exact pending-cue report. Never
mark unresolved wording reviewed merely to export it. Keep the original unchanged
and report unresolved linguistic questions separately from technical checks.
