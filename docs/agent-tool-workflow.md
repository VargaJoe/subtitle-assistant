# Agent tool workflow — API 1.1, workspace schema 2

The external agent supplies translations using its own model. The shared service
stores and validates them; neither CLI nor HTTP starts a translation provider.
Python 3.10+ and the standard library suffice. Run the following from the repository
root, or install with `python -m pip install --no-deps .` and replace
`python -S -m subtitle_translator.tool` with `subtitle-assistant`.

## Direct CLI

Use an explicit absolute workspace. These examples use PowerShell variables:

```powershell
$work = 'D:\path\subtitle-workspace'
python -S -m subtitle_translator.tool doctor --workspace $work --json
python -S -m subtitle_translator.tool project import --input 'D:\path\source.srt' --source en --target hu --workspace $work --json
python -S -m subtitle_translator.tool project list --workspace $work --json
python -S -m subtitle_translator.tool project status --project <project_id> --workspace $work --json
```

Every command with `--json` returns one envelope: `ok`, `api_version`,
`request_id`, `warnings`, and `data` or `error`. Errors exit 1. Mutations accept UUID
request IDs. Save exact UTF-8 JSON request files before sending; the examples below
use placeholders that must be replaced with returned values and real UUIDs.

Prepare with `batch prepare --request prepare.json --workspace $work --json`:

```json
{"request_id":"<uuid>","project_id":"<project_id>","expected_project_revision":1,"max_chars":6000,"context_before":2,"context_after":2,"actor":"Cody"}
```

The returned `data.batch` includes `batch_id`, source hash, content/context
revisions and `units`. Each unit includes stable cue IDs, source text/times,
formatting runs, surrounding source/target context and `writable_entry_ids`.
Grouping uses sentence-continuation and formatting heuristics. It is conservative
input preparation, not verified speaker or scene recognition. A unit is never cut
to meet `max_chars`; increase the budget on `unit_too_large`.

Translate units together, then assign the translated phrases to the original cue
IDs. New display rows within a cue are allowed. Return every writable cue exactly
once, without timestamps. Submit using `batch submit --request submit.json`:

```json
{
  "request_id":"<uuid>","batch_id":"<batch_id>",
  "expected_project_revision":1,"source_sha256":"<returned hash>",
  "context_revision":0,"actor":"Cody",
  "translations":[{"unit_id":"<unit_id>","entries":[
    {"entry_id":"<cue_id>","text":"A teljes csoport alapján fordított szöveg.","state":"translated","review_state":"agent_reviewed"}
  ]}]
}
```

States: `draft`, `needs_review`, `translated`, `intentionally_preserved`. Final
states require `agent_reviewed` or `human_reviewed`; unchecked work stays incomplete.
Intentional preservation must retain source wording. Markup supports `i`, `b`,
`u`, `font`; ambiguous or unsupported source markup requires source review.
Full-cue styles, partial emphasis, speaker and accessibility markers are checked;
partial emphasis and semantic placement still need linguistic review.

A successful submission is atomic and advances the project revision. Missing,
duplicate, unknown or protected IDs reject the whole batch. No source-text
fallback or positional padding is used. Repeating the exact UUID/payload returns
its saved result. Fetch a prepared batch with `batch get --batch <id>`.

```powershell
python -S -m subtitle_translator.tool request receipt --request-id <uuid> --workspace $work --json
python -S -m subtitle_translator.tool issue list --project <id> --workspace $work --json
python -S -m subtitle_translator.tool project validate --project <id> --workspace $work --json
python -S -m subtitle_translator.tool project export --project <id> --variant target --expected-revision <revision> --output 'D:\path\new.hu.srt' --workspace $work --json
```

Source validation can succeed while `target_ready` is false. Target export requires
all cues reviewed at current source/timing/context revisions, then rechecks markup
and exact cue index/start/stop mapping after display wrapping. `source` exports the
working source; `original` exports the archived original bytes. Outputs never
overwrite existing files or the imported source. Manual source/timing edits are
the only operations allowed to change working anchors.

## Editing, history and supervision

`entry edit --request edit.json` accepts:

```json
{"request_id":"<uuid>","project_id":"<id>","entry_id":"<cue_id>","expected_project_revision":2,"actor":"Joe","changes":{"target_text":"Kézzel javított szöveg.","review_state":"human_reviewed"}}
```

Allowed changes: `source_text`, `start_ms`, `end_ms`, `target_text`, `protected`,
`review_state`, `clear_target`. Target edits are protected by default. Explicit
`protected:false` allows future agent writes. `clear_target:true` removes a target
and cannot accompany target/review/protection fields. Source/timing edits mark an
existing translation for review and invalidate prepared batches. Every saved cue
change has before/after history, including batch submissions.

Read `entry history --project <id> --entry <cue_id>`. Restore with
`entry restore --request restore.json`, containing UUID, project ID, change ID,
current `expected_project_revision`, optional actor. Restore writes a new revision
and history record; restoring stale work does not mark it reviewed.

Report activity using `job activity --request activity.json`:

```json
{"request_id":"<uuid>","project_id":"<id>","agent_label":"Cody","phase":"translating","batch_id":"<active_batch_id>","ttl_seconds":120}
```

Phases: `starting`, `analyzing`, `translating`, `validating`, `waiting`, `paused`,
`finished`, `failed`. Activity never increments content revision. `job status`
returns state, phase, `freshness` (`fresh`, `stale`, `unknown`) and completed counts.
An expired heartbeat does not imply completion. Actor labels are metadata.

`job control --request control.json` takes UUID, project ID and `action`:
`pause`, `resume`, `cancel`. Pause is cooperative: `pause_requested` allows the
already running batch to finish atomically, then becomes `paused`; a well-behaved
agent checks status before submitting and acknowledges pause instead. Cancellation
immediately invalidates prepared batches. Pause/cancel never resume from ordinary
activity reports. Revisions protect the agent and a later GUI from concurrent edits.

## Local HTTP API

Run `python -S -m subtitle_translator.tool api serve --workspace $work --allowed-root 'D:\path' --json`
in a dedicated process. It binds loopback and chooses a free port by default.
The first stdout line is a readiness envelope; credentials are absent from it.
The generated private `api-connection.json` stays in the workspace. Treat it as a
local credential; do not copy it into prompts, logs or source control.

Use `api call --request operation.json --workspace $work --json` from another
process. It discovers the endpoint and token automatically:

```json
{"operation":"project.status","arguments":{"project_id":"<id>"}}
```

All domain operations in `capabilities` use this envelope. For JSON-request CLI
operations, `arguments` is the same request object. Other operations use service
field names (`input_path`, `output_path`, `project_id`, `expected_revision`, etc.)
defined in [the schemas](schemas/tool-v1.schema.json).

- Public `GET /api/v1/health` checks transport only.
- Authenticated `GET /api/v1/capabilities` and schema discovery describe the tool.
- Authenticated `POST /api/v1/operations` invokes the closed operation set.
- `api stop --workspace $work --json` requests authenticated clean shutdown.

See [OpenAPI](schemas/tool-v1.openapi.json) for exact HTTP paths and responses.
Import/export paths are restricted to `--allowed-root` (default server cwd).
There is no account or client registration. No wildcard CORS is enabled. HTTP
errors retain the domain envelope (400 input, 404 absent, 409 conflict/incomplete,
422 invalid translation, 503 busy). Client proxy/redirect handling cannot forward
the local token. A stopped API returns `api_not_running`/`api_unavailable`;
direct CLI continues using the same persistent project. Do not mutate the
connection file manually to recover a domain error.

## Existing v1 workspace

`doctor` reports `migration_required`. Read-only M1 source operations remain
available. Run `workspace migrate --expected-version 1 --workspace $work --json`
to add schema 2 with an exclusive `before-schema-v1.sqlite3` backup. Existing
backups are never overwritten. New workspaces start at schema 2. Migration is an
administrative operation: it returns its durable schema state rather than a
content-mutation receipt. An interrupted migration requires checking `doctor`
and the reported backup before retrying; do not delete the backup automatically.

## Partial work and draft exports

Save unfinished wording as `draft`/`unchecked` (manual edits default to this),
without claiming a review. It survives reopening the same workspace.
For video testing before review is complete, explicitly request:

```powershell
python -S -m subtitle_translator.tool project export --project <id> --variant draft --expected-revision <revision> --output 'D:\path\new.hu.draft.srt' --workspace $work --json
```

The SRT preserves every current cue index and timing anchor. Pending cues carry
visible review/stale markers; missing translations use marked working-source
text. The response and immutable export receipt contain a `draft` report with
every pending cue ID, ordinal, timestamps and reason. GUI downloads require
confirmation and offer that snapshot as a separate human-readable review list.
The export does not mark anything reviewed or change the saved project.
`target` remains the fully reviewed final export. Structural SRT corruption
still blocks either variant. Use exact request IDs/receipts for draft retries too.

The [early supervised GUI](gui-preview.md) is available. Persistent story/character
memory, provider OAuth, frames and STT remain later milestones.
