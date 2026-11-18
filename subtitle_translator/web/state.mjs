// Pure editor state. The server remains authoritative for revisions and writes.
const fields = ["source_text", "target_text", "start", "end", "protected", "reviewed"];

export function formatTimestamp(value) {
  if (!Number.isSafeInteger(value) || value < 0) throw new Error("Az időpont nem ábrázolható biztonságosan.");
  const ms = value % 1000, seconds = Math.floor(value / 1000);
  return `${String(Math.floor(seconds / 3600)).padStart(2, "0")}:${String(Math.floor(seconds / 60) % 60).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")},${String(ms).padStart(3, "0")}`;
}

export function parseTimestamp(text) {
  const match = /^(\d{2,}):([0-5]\d):([0-5]\d)[,.](\d{3})$/.exec(text.trim());
  if (!match) throw new Error("Az időpont alakja: 00:00:00,000.");
  const value = ((Number(match[1]) * 60 + Number(match[2])) * 60 + Number(match[3])) * 1000 + Number(match[4]);
  if (!Number.isSafeInteger(value)) throw new Error("Az időpont túl nagy a szerkesztőhöz.");
  return value;
}

export function reviewed(entry) {
  return Boolean(entry.target && ["translated", "intentionally_preserved"].includes(entry.target.state)
    && ["agent_reviewed", "human_reviewed"].includes(entry.target.review_state));
}

export function matchesEntry(entry, filter="all", search="") {
  if (filter === "pending" && reviewed(entry)) return false;
  if (filter === "review" && (reviewed(entry) || !entry.target)) return false;
  if (filter === "missing" && entry.target) return false;
  if (filter === "protected" && !entry.target?.protected) return false;
  const query=search.trim().toLocaleLowerCase("hu");
  return !query || `${entry.source_text}\n${entry.target?.text || ""}\n${entry.ordinal}`.toLocaleLowerCase("hu").includes(query);
}

export function targetReadiness(entries, job, revision, validation=null) {
  const pending=entries.filter(entry=>!reviewed(entry));
  const current=validation?.revision === revision ? validation : null;
  return {total:entries.length, reviewedCount:entries.length-pending.length, pending,
    missingCount:entries.filter(entry=>!entry.target?.text?.trim()).length,
    agentFinished:job?.phase === "finished" || job?.state === "completed",
    state:pending.length ? "review" : current?.status === "complete"
      ? current.target_ready === true ? "ready" : "invalid"
      : current?.status === "error" ? "error" : "checking",
    issue:current?.issue || null};
}

export function targetExportPlan(view, projectId, revision) {
  if (!["ready", "review", "invalid"].includes(view.state)) return null;
  const variant=view.state === "ready" ? "target" : "draft";
  return {projectId,revision,variant,requiresConfirmation:variant === "draft",
    pendingCount:view.pending.length,missingCount:view.missingCount,
    validationIssue:view.state === "invalid" ? view.issue : null};
}

export function exportPlanCurrent(plan, projectId, revision) {
  return Boolean(plan && plan.projectId === projectId && plan.revision === revision);
}

export function draftReviewDownloadUrl(requestId) {
  return typeof requestId === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(requestId)
    ? `/ui/download/${requestId}/review` : null;
}

const uncertainErrors=new Set(["transport_unknown", "invalid_api_response", "io_error",
  "internal_error", "workspace_error", "export_write_error"]);

export function pendingAfterError(pending, code) {
  return pending && (!code || uncertainErrors.has(code)) ? {...pending, resultState:"unknown"} : null;
}

export function restorePending(pending) {
  return pending ? {...pending, resultState:"restored"} : null;
}

export function pendingWarningVisible(pending) {
  return Boolean(pending && ["unknown", "restored"].includes(pending.resultState));
}

export function valuesOf(entry) {
  return {source_text: entry.source_text, target_text: entry.target?.text ?? "",
    start: formatTimestamp(entry.start_ms), end: formatTimestamp(entry.end_ms),
    protected: entry.target ? Boolean(entry.target.protected) : true, reviewed: reviewed(entry)};
}

export function fingerprint(entry) {
  return JSON.stringify([entry.entry_id, entry.source_revision, entry.timing_revision,
    entry.source_text, entry.start_ms, entry.end_ms, entry.target?.text ?? null,
    entry.target?.state ?? null, entry.target?.review_state ?? null, Boolean(entry.target?.protected)]);
}

export function newDraft(entry, revision) {
  return {entryId: entry.entry_id, base: structuredClone(entry), baseRevision: revision,
    values: valuesOf(entry), reviewTouched: false, conflict: null};
}

export function dirtyFields(draft) {
  const base = valuesOf(draft.base);
  return fields.filter(key => draft.values[key] !== base[key] && (key !== "reviewed" || draft.reviewTouched));
}

export function isDirty(draft) { return dirtyFields(draft).length > 0; }

export function changeField(draft, key, value) {
  const next = {...draft, values: {...draft.values, [key]: value}};
  if (key === "reviewed") next.reviewTouched = true;
  if (["source_text", "target_text", "start", "end"].includes(key)) {
    next.values.reviewed = false;
    next.reviewTouched = false;
  }
  if (key === "target_text" && value !== (draft.base.target?.text ?? "")) next.values.protected = true;
  return next;
}

export function mergeDraft(draft, current, revision) {
  if (!isDirty(draft)) return newDraft(current, revision);
  if (fingerprint(draft.base) === fingerprint(current)) {
    // Other cues changed; the fields being edited are still based on current data.
    return {...draft, baseRevision: revision, conflict: null};
  }
  return {...draft, conflict: {entry: structuredClone(current), revision}};
}

export function rebaseDraft(draft) {
  if (!draft.conflict) return draft;
  const next = newDraft(draft.conflict.entry, draft.conflict.revision);
  for (const key of dirtyFields(draft)) next.values[key] = draft.values[key];
  next.reviewTouched = draft.reviewTouched;
  if (["source_text", "target_text", "start", "end"].some(key => dirtyFields(draft).includes(key)) && !draft.reviewTouched) next.values.reviewed = false;
  return next;
}

export function changesFor(draft) {
  if (draft.conflict) throw new Error("Előbb válaszd ki, hogyan kezeled a közben érkezett változást.");
  const {values, base} = draft;
  if (!values.source_text.trim()) throw new Error("A forrásszöveg nem lehet üres.");
  const start = parseTimestamp(values.start), end = parseTimestamp(values.end);
  if (end <= start) throw new Error("A befejezésnek a kezdés után kell lennie.");
  const changes = {};
  if (values.source_text !== base.source_text) changes.source_text = values.source_text;
  if (start !== base.start_ms) changes.start_ms = start;
  if (end !== base.end_ms) changes.end_ms = end;
  const targetChanged = values.target_text !== (base.target?.text ?? "");
  const reviewChanged = draft.reviewTouched && (values.reviewed !== reviewed(base)
    || Object.keys(changes).length > 0);
  if (targetChanged || reviewChanged) {
    if (!values.target_text.trim()) throw new Error("A fordítás nem lehet üres. A korábbi szöveg az előzményekből visszaállítható.");
    changes.target_text = values.target_text;
    changes.review_state = values.reviewed ? "human_reviewed" : "unchecked";
    changes.protected = values.protected;
  } else if (base.target && values.protected !== Boolean(base.target.protected)) changes.protected = values.protected;
  if (!Object.keys(changes).length) throw new Error("Nincs mentendő módosítás.");
  return changes;
}
