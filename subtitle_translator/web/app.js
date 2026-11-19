import {formatTimestamp, parseTimestamp, reviewed, fingerprint, newDraft, isDirty,
  changeField, mergeDraft, rebaseDraft, changesFor, matchesEntry, targetReadiness,
  pendingAfterError, restorePending, pendingWarningVisible, targetExportPlan, exportPlanCurrent,
  draftReviewDownloadUrl} from "./state.mjs";

const $ = id => document.getElementById(id);
const app = {config:null, projectId:null, project:null, revision:null, entries:[], byId:new Map(),
  rows:new Map(), drafts:new Map(), selectedId:null, job:null, batch:null, projects:[],
  connected:false, busy:false, busyKind:null, pending:null, targetValidation:null,
  exportConfirmation:null, draftExports:new Map(),
  refreshing:false, refreshAgain:false, stopped:false};
const stateLabels = {pending:"Várakozik",running:"Dolgozik",pause_requested:"Szünet kérve",
  paused:"Szünetel",cancelled:"Beküldés leállítva",failed:"Hiba",completed:"Befejezte a munkát"};
const phaseLabels = {starting:"Előkészítés",analyzing:"Szöveg áttekintése",translating:"Fordítás",
  validating:"Ellenőrzés",waiting:"Várakozás",paused:"Szünet visszaigazolva",finished:"Az agent befejezte a munkafázist",failed:"Hibajelzés"};
const errorMessages = {
  unauthorized:"A helyi kapcsolat lejárt. Indítsd el újra a Feliratműhelyt az indítóval.",
  revision_conflict:"Közben módosult a projekt. A javításod megmaradt; töltsd be és hasonlítsd össze a friss állapotot.",
  translation_incomplete:"Még van hiányzó vagy ellenőrizendő fordítás. Ellenőrizd a javításokat, vagy tölts le jelölt munkaváltozatot.",
  invalid_timestamp:"Az időpont hibás. A befejezésnek a kezdés után kell lennie.",
  invalid_translation:"A szöveg nem lehet üres és nem tartalmazhat üres feliratblokkot.",
  invalid_subtitle:"A fájlban hibás SRT-bejegyzés van. A projekt nem jött létre; ellenőrizd a felirat szerkezetét.",
  source_encoding_error:"A fájl karakterkódolása nem megfelelő. Válassz másik kódolást a megnyitásnál.",
  source_formatting_requires_review:"A forrás formázását előbb javítani kell.",
  invalid_translation_formatting:"A fordítás formázási jelölése hiányos vagy nem támogatott.",
  formatting_scope_changed:"A fordítás formázása eltér a forrástól. Ellenőrizd a kiemelések hatókörét.",
  speaker_markers_changed:"A beszélőjelölések megváltoztak. Ellenőrizd a párbeszéd sorainak jelölését.",
  accessibility_markers_changed:"Hang- vagy zenejelölés hiányzik a fordításból.",
  timing_anchor_changed:"A fordítás formázása megváltoztatná az időzített bejegyzések határait. Ellenőrizd a szöveget és a sortöréseket.",
  workspace_busy:"A munkatér most foglalt. A javításod megmaradt; próbáld újra rövidesen.",
  workspace_migration_required:"A munkatér korábbi változatú; a szerkesztéshez frissíteni kell.",
  migration_backup_exists:"Már létezik korábbi migrációs mentés. Nem írjuk felül; a munkatér állapotát ellenőrizni kell.",
  request_id_conflict:"Ez a kérésazonosító már más tartalomhoz tartozik. A korábbi mentést nem módosítottuk.",
  file_too_large:"A felirat túl nagy ehhez a megnyitási módhoz.",
  request_too_large:"A felirat túl nagy ehhez a megnyitási módhoz.",
  job_not_running:"A munka szünetel vagy leállt. A folytatást külön kell kérni.",
  invalid_ticket:"A megnyitási hivatkozás lejárt vagy már felhasználták. Használd újra a helyi indítót.",
  source_integrity_error:"Az archivált eredeti sértetlensége nem igazolható. Az export leállt.",
  project_integrity_error:"A projekt exportellenőrzése hibát talált. A mentett adatokat nem írtuk felül."
};

class ToolError extends Error {
  constructor(error) { super(errorMessages[error.code] || error.message || "A művelet nem sikerült."); this.code=error.code; this.details=error.details; }
}

function notify(message, kind="info", action=null) {
  const box=$("global-message");
  box.className=`notice ${kind === "error" ? "error" : kind === "warning" ? "warning" : ""}`;
  box.replaceChildren(document.createTextNode(message)); box.hidden=false;
  if (action) {
    const button=document.createElement("button"); button.className="button compact";
    button.textContent=action.label; button.addEventListener("click",action.run);
    const wrapper=document.createElement("div"); wrapper.className="notice-actions"; wrapper.append(button); box.append(wrapper);
  }
  if (kind === "error" || action) {
    const bounds=box.getBoundingClientRect();
    if (bounds.top < 0 || bounds.bottom > innerHeight) box.scrollIntoView({block:"nearest"});
  }
}

function showError(error) { notify(error.message || String(error),"error"); }

function connection(online, label=null) {
  app.connected=online;
  const el=$("connection-status"); el.className=`connection${online ? "" : " offline"}`;
  el.replaceChildren(Object.assign(document.createElement("i"),{}), document.createTextNode(label || (online ? "Helyben kapcsolódva" : "Nincs kapcsolat")));
}

async function request(path, body, method=body === undefined ? "GET" : "POST") {
  const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),15000);
  try {
  let response;
  try {
    const headers={"Accept":"application/json"};
    if (body !== undefined) { headers["Content-Type"]="application/json"; headers["X-Subtitle-UI"]="1"; }
    response=await fetch(path,{method,credentials:"same-origin",headers,
      body:body === undefined ? undefined : JSON.stringify(body),signal:controller.signal,cache:"no-store"});
  } catch (error) {
    connection(false);
    const failure=new Error("A helyi kiszolgáló nem érhető el. Indítsd el a Start-SubtitleAssistant.cmd fájlt; a böngészőlap önmagában nem indítja el. A mentetlen javításaid megmaradtak, a függő kérés azonos kérésként újraküldhető.");
    failure.code="transport_unknown"; throw failure;
  }
  // A reached server with a malformed response is a different failure from a
  // stopped/unreachable server. Neither proves that a pending write failed.
  let envelope;
  try {
    envelope=await response.json();
    if (typeof envelope?.ok !== "boolean") throw new Error("Invalid envelope");
  } catch {
    const failure=new Error(`A helyi kiszolgáló hibás választ adott (HTTP ${response.status}). A függő mentés nyugtáját ellenőrizd; a kérésazonosítót megőriztük.`);
    failure.code="invalid_api_response"; throw failure;
  }
  connection(response.status !== 401,response.status === 401 ? "Kapcsolódás szükséges" : null);
  return envelope;
  } finally { clearTimeout(timer); }
}

async function operation(name, arguments_={}) {
  const result=await request("/api/v1/operations",{operation:name,arguments:arguments_});
  if (!result.ok) throw new ToolError(result.error);
  return result.data;
}

function pendingKey() { return `subtitle-assistant.pending:${app.config.workspace}`; }
function persistPending() {
  try { if (app.pending) sessionStorage.setItem(pendingKey(),JSON.stringify(app.pending)); else sessionStorage.removeItem(pendingKey()); }
  catch { /* The exact request also remains in memory if browser storage is full. */ }
  $("pending-panel").hidden=!pendingWarningVisible(app.pending);
}

function setBusy(value, kind=null) {
  app.busy=value; app.busyKind=kind; document.body.classList.toggle("busy",value);
  renderEditor(); renderJob();
  for (const id of ["import-submit","export-source","export-target","pending-receipt","pending-retry","stop-server"]) $(id).disabled=value || (Boolean(app.pending) && !id.startsWith("pending-"));
  renderReadiness();
}

async function mutation(kind, path, operationName, arguments_, meta={}) {
  if (app.busy || app.pending) { notify("Előbb fejezd be vagy ellenőrizd a folyamatban lévő mentést.","warning"); return; }
  const args={...arguments_,request_id:crypto.randomUUID()};
  app.pending={kind,path,operation:operationName,args,meta,resultState:"in_flight"}; persistPending();
  return sendPending();
}

async function sendPending() {
  const pending=app.pending; if (!pending || app.busy) return;
  setBusy(true,pending.kind);
  try {
    const body=pending.operation ? {operation:pending.operation,arguments:pending.args} : pending.args;
    const response=await request(pending.path,body);
    if (!response.ok) {
      app.pending=pendingAfterError(pending,response.error.code); persistPending();
      throw new ToolError(response.error);
    }
    app.pending=null; persistPending();
    await applyMutation(pending,response.data);
    return response.data;
  } catch (error) {
    if (app.pending) { app.pending=pendingAfterError(pending,error.code); persistPending(); }
    showError(error);
    if (pending.kind === "import") { $("import-error").textContent=error.message; $("import-error").hidden=false; }
    if (error.code === "revision_conflict") await refreshProject(true).catch(showError);
  } finally { setBusy(false); }
}

async function checkReceipt() {
  const pending=app.pending; if (!pending || app.busy) return;
  setBusy(true);
  try {
    const receipt=await operation("request.receipt",{request_id:pending.args.request_id});
    if (receipt.state !== "completed") { notify("A mentés még folyamatban van. Szükség esetén ugyanazt a kérést küldd újra.","warning"); return; }
    app.pending=null; persistPending();
    await applyMutation(pending,receipt.result);
  } catch(error) {
    if (error.code === "request_not_found") notify("Ehhez a kéréshez még nincs nyugta. Az azonos kérés újraküldése nem duplikálja a mentést.","warning");
    else showError(error);
  } finally { setBusy(false); }
}

function download(url) {
  const link=document.createElement("a"); link.href=url; link.download=""; document.body.append(link); link.click(); link.remove();
}

function draftExportsKey() { return `subtitle-assistant.draft-exports:${app.config.workspace}`; }

function renderDraftExport() {
  const record=app.draftExports.get(app.projectId), url=draftReviewDownloadUrl(record?.requestId);
  $("draft-export-notice").hidden=!url;
  if (!url) return;
  $("draft-export-detail").textContent=`${record.revision}. mentett változat · ${record.pendingCount} ellenőrizendő bejegyzés, ebből ${record.missingCount} fordítás nélkül. A jelölt SRT további ellenőrzést igényel; a letöltés nem állítja átnézettre a bejegyzéseket.`;
  $("draft-review-download").href=url;
}

async function applyMutation(pending, data) {
  if (pending.kind === "import") {
    $("import-dialog").close(); await loadProjects(); await selectProject(data.project.project_id);
    const warnings=data.inspection?.warning_count || 0;
    notify(`A felirat megnyílt. ${data.project.entry_count} bejegyzés${warnings ? ` · ${warnings} figyelmeztetés` : ""}.`);
  } else if (pending.kind === "export") {
    download(data.download_url || `/ui/download/${pending.args.request_id}`);
    if (pending.args.variant === "draft") {
      const record={requestId:pending.args.request_id,revision:pending.args.expected_revision,
        pendingCount:data.draft?.pending_count ?? pending.meta?.pendingCount ?? 0,
        missingCount:data.draft?.missing_count ?? pending.meta?.missingCount ?? 0};
      app.draftExports.set(pending.args.project_id,record);
      try { sessionStorage.setItem(draftExportsKey(),JSON.stringify([...app.draftExports])); } catch {}
      renderDraftExport();
      notify("A DRAFT munkaváltozat letöltése elindult. Az ellenőrzési lista külön is letölthető a projekt állapotánál.","warning");
    } else notify("Az SRT elkészült, a letöltés elindult. A munkatér exports mappájában is megmarad.");
  } else {
    if (["save","restore"].includes(pending.kind)) {
      app.drafts.delete(pending.meta.entry_id);
      if (pending.kind === "restore") $("history-dialog").close();
      notify(pending.kind === "save" ? "A javítás mentve. Az eredeti felirat változatlan." : "A korábbi változat visszaállítva, új előzményként mentve.");
    } else notify({pause:"A szünetkérés elküldve. Várjuk az agent visszajelzését.",resume:"A munka folytatható.",cancel:"A folyamatban lévő csomag visszavonva. További eredménye nem írható be."}[pending.meta.action] || "A művelet mentve.");
    await refreshProject(true); await loadProjects();
  }
}

async function loadProjects() {
  const items=[]; let cursor=null;
  do { const page=await operation("project.list",{limit:500,cursor}); items.push(...page.items); cursor=page.next_cursor; } while(cursor);
  app.projects=items;
  const nodes=items.map(project=>{
    const button=document.createElement("button"); button.type="button"; button.className=`project-item${project.project_id === app.projectId ? " active" : ""}`;
    button.setAttribute("aria-current",project.project_id === app.projectId ? "page" : "false");
    const title=document.createElement("strong"); title.textContent=project.name;
    const sub=document.createElement("small"); sub.textContent=`${project.source_language.toUpperCase()} → ${project.target_language.toUpperCase()} · ${project.entry_count} bejegyzés`;
    button.append(title,sub); button.addEventListener("click",()=>selectProject(project.project_id).catch(showError)); return button;
  });
  if (!nodes.length) { const note=document.createElement("p"); note.className="sidebar-note"; note.textContent="A megnyitott felirataid itt jelennek meg."; nodes.push(note); }
  $("project-list").replaceChildren(...nodes);
  if (!app.projectId) { $("welcome").hidden=false; $("project-content").hidden=true; }
}

async function selectProject(projectId) {
  if (app.projectId === projectId && app.entries.length) return;
  app.projectId=projectId; app.project=null; app.revision=null; app.entries=[]; app.byId.clear(); app.rows.clear(); app.selectedId=null; app.job=null; app.batch=null; app.targetValidation=null;
  $("cue-list").replaceChildren(); $("editor").hidden=true;
  $("welcome").hidden=true; $("project-content").hidden=false; $("project-title").textContent="Projekt betöltése…";
  $("export-source").disabled=true; $("export-target").disabled=true; $("export-target").textContent="Fordítás ellenőrzése…";
  $("readiness-card").className="readiness-card checking";
  $("readiness-title").textContent="A fordítás állapotának betöltése…";
  $("readiness-count").textContent=""; $("readiness-detail").textContent="";
  $("review-pending").hidden=true; $("retry-validation").hidden=true;
  $("draft-export-notice").hidden=true;
  document.body.classList.remove("sidebar-open"); $("sidebar-toggle").setAttribute("aria-expanded","false");
  try { sessionStorage.setItem(`subtitle-assistant.project:${app.config.workspace}`,projectId); } catch {}
  await refreshProject(true); await loadProjects();
}

async function readEntries(projectId) {
  for (let attempt=0;attempt<3;attempt++) {
    let cursor=null, revision=null, consistent=true; const items=[];
    do {
      const page=await operation("entry.list",{project_id:projectId,limit:500,cursor});
      if (revision === null) revision=page.revision;
      if (page.revision !== revision) { consistent=false; break; }
      items.push(...page.items); cursor=page.next_cursor;
    } while(cursor);
    if (consistent) return {items,revision};
  }
  throw new Error("A projekt most gyorsan változik. A következő frissítésnél újra betöltjük; a saját javításod megmaradt.");
}

async function refreshProject(force=false) {
  if (!app.projectId || app.stopped) return;
  if (app.refreshing) { app.refreshAgain ||= force; return; }
  app.refreshing=true; const projectId=app.projectId;
  try {
    const [status,job]=await Promise.all([operation("project.status",{project_id:projectId}), operation("job.status",{project_id:projectId})]);
    if (app.projectId !== projectId) return;
    app.project=status.project; app.job=job;
    if (force || app.revision !== status.project.revision) {
      const page=await readEntries(projectId); if (app.projectId !== projectId) return;
      app.entries=page.items; app.byId=new Map(page.items.map(entry=>[entry.entry_id,entry])); app.revision=page.revision;
      app.project.revision=page.revision;
      for (const entry of app.entries) {
        if (app.drafts.has(entry.entry_id)) app.drafts.set(entry.entry_id,mergeDraft(app.drafts.get(entry.entry_id),entry,app.revision));
      }
      renderRows();
      if (!app.selectedId || !app.byId.has(app.selectedId)) selectEntry(app.entries[0]?.entry_id);
      else {
        if (!app.drafts.has(app.selectedId)) app.drafts.set(app.selectedId,newDraft(app.byId.get(app.selectedId),app.revision));
        renderEditor();
      }
    }
    renderProject(); renderJob(); renderReadiness();
    void ensureTargetValidation();
    const jobKey=JSON.stringify([job.state,job.freshness,job.batch_id]);
    if (app.lastJobKey !== jobKey) { app.lastJobKey=jobKey; renderRows(); }
    if (job.batch_id && app.batch?.batch_id !== job.batch_id) {
      const currentBatchId=job.batch_id;
      try {
        const {batch}=await operation("batch.get",{batch_id:currentBatchId});
        if (app.projectId === projectId && app.job?.batch_id === currentBatchId) { app.batch=batch; renderJob(); renderRows(); }
      } catch { /* A concurrently closed batch is represented by the next job update. */ }
    } else if (!job.batch_id) app.batch=null;
  } finally {
    app.refreshing=false;
    if (app.refreshAgain || app.projectId !== projectId) { app.refreshAgain=false; queueMicrotask(()=>refreshProject(true).catch(showError)); }
  }
}

function renderProject() {
  if (!app.project) return;
  const p=app.project, source=p.source_language.toUpperCase(), target=p.target_language.toUpperCase();
  $("project-title").textContent=p.name; $("breadcrumb-project").textContent=p.name;
  $("project-languages").textContent=`${source} → ${target} · FELIRATPROJEKT`;
  $("project-meta").textContent=`${p.entry_count} időzített bejegyzés · ${app.revision}. mentett változat · az eredeti megőrizve`;
  $("source-column").textContent=`FORRÁS · ${source}`; $("target-column").textContent=`FORDÍTÁS · ${target}`;
  $("source-language-label").textContent=source; $("target-language-label").textContent=target;
  $("target-editor").lang=p.target_language;
  document.title=`${p.name} · Feliratműhely`;
}

function readiness() {
  return targetReadiness(app.entries,app.job,app.revision,app.targetValidation);
}

function issueMessage(issue) {
  return errorMessages[issue?.code] || issue?.message || "Az export ellenőrzése nem sikerült. Ellenőrizd a fordítást.";
}

function renderReadiness() {
  if (!app.project) return;
  const view=readiness(), plan=targetExportPlan(view,app.projectId,app.revision), blocked=app.busy || Boolean(app.pending) || Boolean(app.exportConfirmation);
  // Polling must not repeatedly announce an unchanged live status card.
  const text=(id,value)=>{ if ($(id).textContent !== value) $(id).textContent=value; };
  const titles={review:`${view.pending.length} bejegyzés ellenőrzésre vár`,checking:"Az export ellenőrzése folyamatban",
    ready:"A fordítás letölthető",invalid:"A fordítás exportja javítást igényel",error:"Az export ellenőrzése nem sikerült"};
  text("readiness-title",`${view.agentFinished ? "Az agent végzett · " : ""}${titles[view.state]}`);
  $("readiness-card").className=`readiness-card ${view.state}`;
  text("readiness-count",`${view.reviewedCount} / ${view.total} átnézett bejegyzés`);
  let detail;
  if (view.state === "review") {
    const ordinals=view.pending.slice(0,12).map(entry=>`#${entry.ordinal}`).join(", ");
    detail=`Hiányzó vagy még nem átnézett fordítás: ${ordinals}${view.pending.length > 12 ? ` és további ${view.pending.length-12}` : ""}. Megerősítéssel jelölt munkaváltozat és ellenőrzési lista tölthető le.`;
  } else if (["invalid","error"].includes(view.state)) detail=`${issueMessage(view.issue)}${view.state === "invalid" ? " Megerősítéssel munkaváltozat kérhető; az SRT szerkezetét a kiszolgáló ellenőrzi." : ""}`;
  else if (view.state === "ready") detail="A mentett fordítás és az SRT szerkezete sikeresen ellenőrizve.";
  else detail="Az átnézettség után a mentett szöveg formázását és az SRT szerkezetét is ellenőrizzük.";
  text("readiness-detail",detail);
  $("review-pending").hidden=!["review","invalid"].includes(view.state);
  $("review-pending").textContent=view.state === "review" ? "Hiányzó és ellenőrizendő megmutatása" : "Bejegyzések megtekintése";
  $("review-pending").disabled=blocked;
  $("retry-validation").hidden=view.state !== "error";
  $("retry-validation").disabled=blocked;
  $("export-target").textContent=view.state === "ready" ? "Fordítás letöltése ↓"
    : plan?.variant === "draft" ? "Munkaváltozat letöltése ↓"
    : view.state === "checking" ? "Export ellenőrzése…" : "Export újraellenőrzése";
  $("export-target").disabled=blocked || view.state === "checking";
  $("export-source").disabled=blocked;
  renderDraftExport();
}

async function ensureTargetValidation(force=false) {
  if (!app.project || app.entries.length !== app.project.entry_count || readiness().pending.length) return;
  const projectId=app.projectId, revision=app.revision;
  if (app.targetValidation?.revision === revision && (!force || app.targetValidation.status === "checking")) return;
  const validation={projectId,revision,status:"checking"};
  app.targetValidation=validation; renderReadiness();
  try {
    const result=await operation("project.validate",{project_id:projectId});
    if (app.projectId !== projectId || app.revision !== revision || app.targetValidation !== validation) return;
    if (result.revision !== revision) {
      app.targetValidation=null;
      void refreshProject(true).catch(showError);
      return;
    }
    app.targetValidation={...validation,status:"complete",target_ready:result.target_ready,
      issue:result.target_issue || null};
  } catch (error) {
    if (app.projectId !== projectId || app.revision !== revision || app.targetValidation !== validation) return;
    app.targetValidation={...validation,status:"error",issue:{code:error.code,message:error.message}};
  } finally {
    if (app.projectId === projectId) renderReadiness();
  }
}

function showReviewEntries() {
  const view=readiness();
  $("search").value="";
  $("filter").value=view.pending.length ? "pending" : "all";
  const issueIds=view.issue?.details?.entry_ids || [view.issue?.details?.entry_id];
  const first=view.pending[0] || app.entries.find(entry=>issueIds.includes(entry.entry_id)) || app.byId.get(app.selectedId) || app.entries[0];
  renderRows();
  if (first) selectEntry(first.entry_id,true);
}

function renderJob() {
  if (!app.job) return;
  const job=app.job, stale=job.freshness === "stale";
  const active=job.state === "running" && !stale;
  $("agent-name").textContent=job.agent_label || "Nincs aktív agent";
  $("job-state").textContent=stale && ["running","pause_requested"].includes(job.state) ? "Elavult munkajelzés" : stateLabels[job.state] || job.state;
  $("job-state").className=`badge ${stale && ["running","pause_requested"].includes(job.state) ? "warning" : ["paused","pause_requested"].includes(job.state) ? "warning" : job.state === "failed" ? "danger" : ""}`;
  const detail=[];
  if (stale && ["running","pause_requested"].includes(job.state)) detail.push("Az agent nem adott friss életjelet; nem tudjuk, dolgozik-e még.");
  else if (job.state === "pause_requested") detail.push("A szünetet kértük, az agent még nem igazolta vissza.");
  else if (!job.agent_label) detail.push("Az agent munkája itt követhető. Kézzel is szerkeszthetsz.");
  else detail.push(phaseLabels[job.phase] || job.phase);
  if (job.batch_id && app.batch?.batch_id === job.batch_id && app.batch.state === "prepared") {
    const ordinals=app.batch.units.flatMap(unit=>unit.source_entries.map(entry=>entry.ordinal));
    detail.push(`Most: #${Math.min(...ordinals)}–${Math.max(...ordinals)}`);
  }
  $("job-detail").textContent=detail.join(" · ");
  $("activity-icon").className=`activity-icon${active ? " working" : ""}${stale && job.state === "running" ? " stale" : ""}`;
  const percent=job.total_entries ? Math.round(100*job.completed_entries/job.total_entries) : 0;
  $("progress-fill").style.width=`${percent}%`; $("job-progress").setAttribute("aria-valuenow",String(percent));
  $("progress-count").textContent=`${job.completed_entries} / ${job.total_entries}`;
  if (job.last_seen === null) $("heartbeat").textContent="Még nincs életjel";
  else {
    const seconds=Math.max(0,Math.floor(Date.now()/1000-job.last_seen));
    $("heartbeat").textContent=`Életjel: ${seconds < 60 ? `${seconds} mp` : seconds < 3600 ? `${Math.floor(seconds/60)} perce` : `${Math.floor(seconds/3600)} órája`}`;
    $("heartbeat").title=new Date(job.last_seen*1000).toLocaleString("hu-HU");
  }
  $("job-pause").hidden=["paused","cancelled","completed","failed"].includes(job.state);
  $("job-pause").disabled=app.busy || Boolean(app.pending) || job.state === "pause_requested";
  $("job-resume").hidden=!["paused","pause_requested","cancelled","failed"].includes(job.state);
  $("job-resume").disabled=app.busy || Boolean(app.pending);
  $("job-cancel").disabled=app.busy || Boolean(app.pending) || job.state === "cancelled" || (!job.agent_label && !job.batch_id);
}

function matches(entry) {
  return matchesEntry(entry,$("filter").value,$("search").value);
}

function rowNodes(entry) {
  const row=document.createElement("div"); row.className="cue-row"; row.role="option"; row.id=`row-${entry.ordinal}`; row.tabIndex=-1;
  const anchor=document.createElement("span"), number=document.createElement("span"), time=document.createElement("span");
  number.className="cue-number"; time.className="cue-time"; anchor.append(number,time);
  const source=document.createElement("span"), target=document.createElement("span"), state=document.createElement("span");
  source.className="cue-text source"; target.className="cue-text"; state.className="cue-state";
  const badge=document.createElement("span"), protection=document.createElement("span"), dirty=document.createElement("span");
  badge.className="badge"; protection.className="protected-label"; dirty.className="dirty-label"; state.append(badge,protection,dirty);
  row.append(anchor,source,target,state); row.addEventListener("click",()=>selectEntry(entry.entry_id));
  row.addEventListener("keydown",event=>{ if (event.key === "Enter" || event.key === " ") { event.preventDefault(); selectEntry(entry.entry_id); $("source-editor").focus(); } });
  return {row,number,time,source,target,badge,protection,dirty,lastFingerprint:null};
}

function renderRows() {
  if (!app.projectId) return;
  let visible=0; const fragment=document.createDocumentFragment();
  const activeOrdinals=app.job?.state === "running" && app.job.freshness === "fresh" && app.batch?.batch_id === app.job.batch_id
    ? new Set(app.batch.units.flatMap(unit=>unit.source_entries.map(entry=>entry.ordinal))) : new Set();
  for (const entry of app.entries) {
    let nodes=app.rows.get(entry.entry_id);
    if (!nodes) { nodes=rowNodes(entry); app.rows.set(entry.entry_id,nodes); fragment.append(nodes.row); }
    const key=fingerprint(entry);
    if (key !== nodes.lastFingerprint) {
      nodes.number.textContent=`#${String(entry.ordinal).padStart(3,"0")}`;
      nodes.time.textContent=`${formatTimestamp(entry.start_ms)} →\n${formatTimestamp(entry.end_ms)}`;
      nodes.source.textContent=entry.source_text; nodes.target.textContent=entry.target?.text || "Még nincs fordítás";
      nodes.target.className=`cue-text${entry.target ? "" : " missing"}`;
      nodes.badge.textContent=reviewed(entry) ? "Átnézve" : entry.target ? "Ellenőrizendő" : "Nincs fordítás";
      nodes.badge.className=`badge${reviewed(entry) ? "" : entry.target ? " warning" : " muted"}`;
      nodes.protection.textContent=entry.target?.protected ? "Kézi védelem" : "";
      nodes.protection.hidden=!entry.target?.protected;
      nodes.lastFingerprint=key;
    }
    const selected=entry.entry_id === app.selectedId;
    nodes.row.classList.toggle("selected",selected); nodes.row.classList.toggle("active-batch",activeOrdinals.has(entry.ordinal));
    nodes.row.setAttribute("aria-selected",String(selected)); nodes.row.tabIndex=selected ? 0 : -1;
    nodes.row.hidden=!matches(entry); if (!nodes.row.hidden) visible++;
    const draft=app.drafts.get(entry.entry_id); nodes.dirty.hidden=!draft || !isDirty(draft); nodes.dirty.textContent="Mentetlen javítás";
  }
  $("cue-list").append(fragment); $("visible-count").textContent=`${visible} / ${app.entries.length}`;
  $("no-matches").hidden=visible !== 0;
  const dirtyCount=[...app.drafts.values()].filter(isDirty).length;
  $("draft-count").textContent=`${dirtyCount} mentetlen javítás`; $("draft-count").hidden=dirtyCount === 0;
}

function selectedDraft() { return app.drafts.get(app.selectedId); }

function selectEntry(entryId, focus=false) {
  if (!entryId || !app.byId.has(entryId)) return;
  app.selectedId=entryId;
  if (!app.drafts.has(entryId)) app.drafts.set(entryId,newDraft(app.byId.get(entryId),app.revision));
  else app.drafts.set(entryId,mergeDraft(app.drafts.get(entryId),app.byId.get(entryId),app.revision));
  $("editor").hidden=false; renderRows(); renderEditor();
  if (focus) { app.rows.get(entryId).row.focus({preventScroll:true}); app.rows.get(entryId).row.scrollIntoView({block:"nearest"}); }
}

function moveEntry(direction, focus=false) {
  const entries=app.entries.filter(matches), index=entries.findIndex(e=>e.entry_id === app.selectedId);
  const next=entries[Math.max(0,Math.min(entries.length-1,index+direction))];
  if (next) selectEntry(next.entry_id,focus);
}

function renderEditor() {
  const draft=selectedDraft(); if (!draft) return;
  const entry=app.byId.get(draft.entryId); if (!entry) return;
  $("editor-title").textContent=`Bejegyzés #${String(entry.ordinal).padStart(3,"0")}`;
  const dirty=isDirty(draft), blocked=Boolean(draft.conflict), saving=app.busyKind === "save" || app.pending?.kind === "save" && app.pending?.meta.entry_id === draft.entryId;
  $("save-status").textContent=saving ? "Mentés ellenőrzése…" : blocked ? "Párhuzamos változás" : dirty ? "Mentetlen javítás" : "Mentve";
  $("save-status").className=`save-status${blocked ? " conflict" : dirty ? " dirty" : ""}`;
  for (const [id,key] of [["source-editor","source_text"],["target-editor","target_text"],["start-time","start"],["end-time","end"]]) {
    if ($(id).value !== draft.values[key]) $(id).value=draft.values[key];
    $(id).disabled=saving;
  }
  $("protect-target").checked=draft.values.protected; $("review-target").checked=draft.values.reviewed;
  $("protect-target").disabled=saving || !draft.values.target_text.trim(); $("review-target").disabled=saving || !draft.values.target_text.trim();
  $("save-edit").disabled=!dirty || blocked || app.busy || Boolean(app.pending);
  $("discard-edit").disabled=!dirty || saving; $("history-open").disabled=app.busy;
  $("conflict-panel").hidden=!blocked;
  if (blocked) {
    const current=draft.conflict.entry;
    $("remote-summary").textContent=`${current.target?.text || "nincs fordítás"} · ${formatTimestamp(current.start_ms)}–${formatTimestamp(current.end_ms)}`;
  }
  try {
    const duration=(parseTimestamp(draft.values.end)-parseTimestamp(draft.values.start))/1000;
    $("duration").textContent=duration > 0 ? `${duration.toLocaleString("hu-HU",{maximumFractionDigits:3})} s` : "Hibás időtartam";
    const plain=draft.values.target_text.replace(/<[^>]*>/g,"").replace(/\s+/g," ").trim();
    const cps=duration > 0 ? plain.length/duration : 0;
    $("reading-speed").textContent=plain ? `${cps > 20 ? "Gyors felirat · " : ""}${cps.toLocaleString("hu-HU",{maximumFractionDigits:1})} karakter/s` : "";
    $("reading-speed").className=`reading-speed${cps > 20 ? " fast" : ""}`;
  } catch { $("duration").textContent="Ellenőrizd az időpontot"; $("reading-speed").textContent=""; }
}

function editField(key, value) {
  const draft=selectedDraft(); if (!draft) return;
  app.drafts.set(draft.entryId,changeField(draft,key,value)); renderEditor(); renderRows();
}

async function saveEdit() {
  const draft=selectedDraft(); if (!draft || app.busy || app.pending) return;
  try {
    const changes=changesFor(draft);
    await mutation("save","/api/v1/operations","entry.edit",{project_id:app.projectId,entry_id:draft.entryId,
      expected_project_revision:draft.baseRevision,actor:"Kézi javítás · GUI",changes},{entry_id:draft.entryId});
  } catch(error) { showError(error); }
}

function openImport() {
  $("import-error").hidden=true; $("import-dialog").showModal();
}

async function importFile(event) {
  event.preventDefault(); const file=$("import-file").files[0]; if (!file) return;
  if (file.size > app.config.max_upload_bytes) { $("import-error").textContent=`A fájl túl nagy. Legfeljebb ${Math.floor(app.config.max_upload_bytes/1024)} KiB nyitható meg itt.`; $("import-error").hidden=false; return; }
  try {
    const bytes=new Uint8Array(await file.arrayBuffer()); let binary="";
    for(let offset=0;offset<bytes.length;offset+=8192) binary+=String.fromCharCode(...bytes.subarray(offset,offset+8192));
    const args={file_name:file.name,content_base64:btoa(binary),source_language:$("import-source").value.trim(),target_language:$("import-target").value.trim(),name:$("import-name").value.trim()};
    if ($("import-encoding").value) args.encoding=$("import-encoding").value;
    await mutation("import","/ui/import",null,args);
  } catch(error) { $("import-error").textContent=error.message; $("import-error").hidden=false; }
}

function hasProjectDrafts() {
  return [...app.drafts.values()].some(d=>app.byId.has(d.entryId) && isDirty(d));
}

async function confirmDraftExport(plan) {
  const dialog=$("draft-export-dialog");
  $("draft-confirm-count").textContent=`${plan.pendingCount} bejegyzés még nincs átnézve; ebből ${plan.missingCount} fordítás nélkül maradt. A hiányzó fordítás helyére a mentett forrásszöveg kerül.`;
  $("draft-confirm-issue").hidden=!plan.validationIssue;
  $("draft-confirm-issue").textContent=plan.validationIssue ? `A végleges export ellenőrzése további hibát jelzett: ${issueMessage(plan.validationIssue)} A munkaváltozatot külön is ellenőrizd.` : "";
  app.exportConfirmation=plan; renderReadiness(); dialog.returnValue="";
  try {
    const closed=new Promise(resolve=>dialog.addEventListener("close",()=>resolve(dialog.returnValue === "download"),{once:true}));
    dialog.showModal();
    return await closed;
  } finally { app.exportConfirmation=null; renderReadiness(); }
}

async function exportProject(variant) {
  if (!app.project || app.busy || app.pending || app.exportConfirmation) return;
  if (hasProjectDrafts()) {
    notify("Előbb mentsd vagy vesd el a projekt mentetlen javításait. A letöltés a mentett változatot tartalmazná.","warning"); return;
  }
  const plan=variant === "target" ? targetExportPlan(readiness(),app.projectId,app.revision)
    : {projectId:app.projectId,revision:app.revision,variant};
  if (!plan) {
    if (readiness().state === "error") await ensureTargetValidation(true);
    return;
  }
  if (plan.requiresConfirmation && !await confirmDraftExport(plan)) return;
  if (!exportPlanCurrent(plan,app.projectId,app.revision)) {
    notify("A megerősítés közben módosult a projekt. Ellenőrizd a friss állapotot, majd kérd újra a letöltést.","warning"); return;
  }
  if (hasProjectDrafts()) {
    notify("Előbb mentsd vagy vesd el a projekt mentetlen javításait.","warning"); return;
  }
  await mutation("export","/ui/export",null,{project_id:plan.projectId,variant:plan.variant,expected_revision:plan.revision},
    {pendingCount:plan.pendingCount,missingCount:plan.missingCount});
}

async function openHistory() {
  const entry=app.byId.get(app.selectedId); if (!entry) return;
  const projectId=app.projectId, entryId=entry.entry_id;
  $("history-title").textContent=`#${String(entry.ordinal).padStart(3,"0")} · Előzmények`;
  $("history-list").textContent="Mentett változatok betöltése…"; $("history-dialog").showModal();
  try {
    const history=await operation("entry.history",{project_id:projectId,entry_id:entryId});
    $("history-list").replaceChildren();
    if (!history.items.length) { $("history-list").textContent="Ehhez a bejegyzéshez még nem történt mentett módosítás."; return; }
    for (const change of [...history.items].reverse()) {
      const item=document.createElement("article"); item.className="history-item";
      const heading=document.createElement("header"), actor=document.createElement("strong"), time=document.createElement("small");
      actor.textContent=change.actor; time.textContent=new Date(change.created_at).toLocaleString("hu-HU"); heading.append(actor,time); item.append(heading);
      const columns=document.createElement("div"); columns.className="history-columns";
      for (const [title,snapshot] of [["Előtte",change.before],["Utána",change.after]]) {
        const section=document.createElement("div"), h=document.createElement("h3"), source=document.createElement("pre"), target=document.createElement("pre"), timing=document.createElement("span");
        h.textContent=title; source.textContent=snapshot.source_text; target.textContent=snapshot.target_text ?? "Nincs fordítás";
        timing.className="history-timing"; timing.textContent=`${formatTimestamp(snapshot.start_ms)} → ${formatTimestamp(snapshot.end_ms)}`;
        section.append(h,timing,source,target); columns.append(section);
      }
      const restore=document.createElement("button"); restore.className="button compact"; restore.textContent="Az előtte álló változat visszaállítása";
      const draft=app.drafts.get(entryId); restore.disabled=app.busy || Boolean(app.pending) || Boolean(draft && isDirty(draft));
      if (restore.disabled) restore.title="Előbb mentsd vagy vesd el a saját javításodat.";
      restore.addEventListener("click",()=>mutation("restore","/api/v1/operations","entry.restore",{
        project_id:projectId,change_id:change.change_id,expected_project_revision:app.revision,actor:"Kézi visszaállítás · GUI"},{entry_id:entryId}));
      item.append(columns,restore); $("history-list").append(item);
    }
  } catch(error) { $("history-list").textContent=error.message; }
}

async function controlJob(action) {
  await mutation("control","/api/v1/operations","job.control",{project_id:app.projectId,action},{action});
}

async function migrateWorkspace() {
  if (app.busy) return; setBusy(true);
  try {
    await operation("workspace.migrate",{expected_version:1});
    $("global-message").hidden=true; await loadProjects();
    if (app.projects.length) await selectProject(app.projects[0].project_id);
    notify("A munkatér frissítve. A korábbi adatbázis mentése a munkatérben megmaradt.");
  } catch(error) { showError(error); }
  finally { setBusy(false); }
}

async function start() {
  try {
    const ticket=new URLSearchParams(location.hash.slice(1)).get("ticket");
    if (location.hash) history.replaceState(null,"",location.pathname);
    if (ticket) { const session=await request("/ui/session",{ticket}); if(!session.ok) throw new ToolError(session.error); }
    const config=await request("/ui/config"); if(!config.ok) throw new ToolError(config.error); app.config=config.data;
    $("workspace-name").textContent=app.config.workspace.split(/[\\/]/).filter(Boolean).at(-1);
    $("workspace-path").textContent=app.config.workspace; $("workspace-path").title=app.config.workspace;
    $("upload-limit").textContent=`SRT-fájl · legfeljebb ${Math.floor(app.config.max_upload_bytes/1024)} KiB`;
    try { app.pending=restorePending(JSON.parse(sessionStorage.getItem(pendingKey()) || "null")); } catch { app.pending=null; }
    try { app.draftExports=new Map(JSON.parse(sessionStorage.getItem(draftExportsKey()) || "[]")); } catch { app.draftExports=new Map(); }
    persistPending();
    setBusy(false);
    const doctor=await operation("doctor");
    if (doctor.migration_required) {
      notify("Ez egy korábbi munkatér. A szerkesztéshez frissítés szükséges; előtte automatikusan adatbázismentés készül.","warning",{label:"Munkatér frissítése",run:migrateWorkspace});
      return;
    }
    await loadProjects();
    let savedProject=null; try { savedProject=sessionStorage.getItem(`subtitle-assistant.project:${app.config.workspace}`); } catch {}
    const project=app.projects.find(p=>p.project_id === savedProject) || app.projects[0];
    if (project) await selectProject(project.project_id);
  } catch(error) {
    showError(error); connection(false,"Kapcsolódás szükséges");
    $("workspace-name").textContent="Nincs megnyitott munkatér";
    $("workspace-path").textContent="Indítsd el újra a Start-SubtitleAssistant indítóval.";
  }
}

for (const id of ["import-open","welcome-import"]) $(id).addEventListener("click",openImport);
$("help-open").addEventListener("click",()=>$("help-dialog").showModal());
for (const button of document.querySelectorAll("[data-close]")) button.addEventListener("click",()=>$(button.dataset.close).close());
$("sidebar-toggle").addEventListener("click",()=>{const open=document.body.classList.toggle("sidebar-open"); $("sidebar-toggle").setAttribute("aria-expanded",String(open));});
$("refresh-projects").addEventListener("click",()=>loadProjects().catch(showError));
$("import-file").addEventListener("change",()=>{const file=$("import-file").files[0]; if(file) $("import-name").value=file.name.replace(/\.srt$/i,"");});
$("import-form").addEventListener("submit",importFile);
$("export-source").addEventListener("click",()=>exportProject("source"));
$("export-target").addEventListener("click",()=>exportProject("target"));
$("review-pending").addEventListener("click",showReviewEntries);
$("retry-validation").addEventListener("click",()=>ensureTargetValidation(true));
$("search").addEventListener("input",renderRows); $("filter").addEventListener("change",renderRows);
$("previous-entry").addEventListener("click",()=>moveEntry(-1,true)); $("next-entry").addEventListener("click",()=>moveEntry(1,true));
for (const [id,key] of [["source-editor","source_text"],["target-editor","target_text"],["start-time","start"],["end-time","end"]]) $(id).addEventListener("input",event=>editField(key,event.target.value));
$("protect-target").addEventListener("change",event=>editField("protected",event.target.checked));
$("review-target").addEventListener("change",event=>editField("reviewed",event.target.checked));
$("save-edit").addEventListener("click",saveEdit);
$("discard-edit").addEventListener("click",()=>{const entry=app.byId.get(app.selectedId); if(entry) {app.drafts.set(entry.entry_id,newDraft(entry,app.revision));renderEditor();renderRows();}});
$("conflict-load").addEventListener("click",()=>{const draft=selectedDraft(); if(draft?.conflict) {app.drafts.set(draft.entryId,newDraft(draft.conflict.entry,draft.conflict.revision));renderEditor();renderRows();}});
$("conflict-keep").addEventListener("click",()=>{const draft=selectedDraft();if(draft) {app.drafts.set(draft.entryId,rebaseDraft(draft));renderEditor();renderRows();}});
$("history-open").addEventListener("click",openHistory);
$("job-pause").addEventListener("click",()=>controlJob("pause")); $("job-resume").addEventListener("click",()=>controlJob("resume")); $("job-cancel").addEventListener("click",()=>controlJob("cancel"));
$("pending-receipt").addEventListener("click",checkReceipt); $("pending-retry").addEventListener("click",sendPending);
$("stop-server").addEventListener("click",async()=>{
  if ([...app.drafts.values()].some(isDirty)) { notify("Előbb mentsd vagy vesd el a mentetlen javításokat.","warning");return; }
  if (app.pending || app.busy) { notify("Előbb ellenőrizd a folyamatban lévő mentést.","warning");return; }
  try { const result=await request("/api/v1/shutdown",{}); if(!result.ok) throw new ToolError(result.error); app.stopped=true;connection(false,"Bezárva");notify("A helyi szolgáltatás leállt. A projekt megmaradt; az indítóval újra megnyitható."); }
  catch(error) {showError(error);}
});
$("cue-list").addEventListener("keydown",event=>{if(["ArrowDown","ArrowUp"].includes(event.key)) {event.preventDefault();moveEntry(event.key === "ArrowDown" ? 1 : -1,true);}});
document.addEventListener("keydown",event=>{
  if (app.exportConfirmation) return;
  if (event.ctrlKey && event.key === "Enter") {event.preventDefault();saveEdit();}
  if (event.ctrlKey && event.key.toLowerCase() === "k") {event.preventDefault();$("search").focus();}
  if (event.altKey && ["ArrowUp","ArrowDown"].includes(event.key)) {event.preventDefault();moveEntry(event.key === "ArrowDown" ? 1 : -1,true);}
});
window.addEventListener("beforeunload",event=>{if(app.pending || [...app.drafts.values()].some(isDirty)) {event.preventDefault();event.returnValue="";}});
setInterval(()=>{if(app.projectId && !app.stopped) refreshProject().catch(error=>{if(error.code !== "transport_unknown") showError(error);});},1500);
await start();
