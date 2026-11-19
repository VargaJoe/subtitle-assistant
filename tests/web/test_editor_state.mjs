import {test} from "node:test";
import assert from "node:assert/strict";
import {formatTimestamp,parseTimestamp,newDraft,changeField,mergeDraft,rebaseDraft,changesFor,isDirty,
  matchesEntry,targetReadiness,pendingAfterError,restorePending,pendingWarningVisible,targetExportPlan,
  exportPlanCurrent,draftReviewDownloadUrl} from "../../subtitle_translator/web/state.mjs";

function cue() { return {entry_id:"cue-1",source_revision:1,timing_revision:1,source_text:"Wait here.",start_ms:1001,end_ms:3100,
  target:{text:"Várj itt!",state:"translated",review_state:"agent_reviewed",protected:0}}; }

test("timestamps retain exact milliseconds and reject lossy or invalid input", () => {
  for (const ms of [0,1,999,60001,3600000,360000001]) assert.equal(parseTimestamp(formatTimestamp(ms)),ms);
  for (const text of ["1:00", "00:60:00,000", "00:00:00,0012", "-01:00:00,000", "999999999999:00:00,000"]) assert.throws(()=>parseTimestamp(text));
  assert.throws(()=>formatTimestamp(Number.MAX_SAFE_INTEGER+1));
});

test("target edits are protected and need an explicit fresh human review", () => {
  let draft=changeField(newDraft(cue(),1),"target_text","Várjon itt!");
  assert.deepEqual(changesFor(draft),{target_text:"Várjon itt!",review_state:"unchecked",protected:true});
  draft=changeField(draft,"reviewed",true);
  assert.equal(changesFor(draft).review_state,"human_reviewed");
  draft=changeField(draft,"target_text","Kérem, várjon!");
  assert.equal(changesFor(draft).review_state,"unchecked");
});

test("source/time-only edit leaves target invalidation to the common service", () => {
  let draft=changeField(newDraft(cue(),4),"source_text","Wait for me.");
  draft=changeField(draft,"end","00:00:04,250");
  assert.deepEqual(changesFor(draft),{source_text:"Wait for me.",end_ms:4250});
  draft=changeField(draft,"reviewed",true);
  assert.equal(changesFor(draft).target_text,"Várj itt!");
  assert.equal(changesFor(draft).review_state,"human_reviewed");
});

test("unrelated revision changes preserve draft and advance its base", () => {
  const draft=changeField(newDraft(cue(),3),"target_text","Várj meg!");
  const merged=mergeDraft(draft,cue(),5);
  assert.equal(merged.values.target_text,"Várj meg!");
  assert.equal(merged.baseRevision,5);
  assert.equal(merged.conflict,null);
});

test("same-cue remote change preserves typing and requires explicit resolution", () => {
  const draft=changeField(newDraft(cue(),1),"target_text","A saját javításom.");
  const current={...cue(),source_text:"Come here.",source_revision:2,target:{...cue().target,text:"Gyere ide!"}};
  const conflicted=mergeDraft(draft,current,2);
  assert.equal(conflicted.values.target_text,"A saját javításom.");
  assert.equal(conflicted.baseRevision,1);
  assert.throws(()=>changesFor(conflicted));
  const rebased=rebaseDraft(conflicted);
  assert.equal(rebased.baseRevision,2);
  assert.equal(rebased.values.source_text,"Come here."); // untouched remote field survives
  assert.equal(rebased.values.target_text,"A saját javításom.");
  assert.deepEqual(changesFor(rebased),{target_text:"A saját javításom.",protected:true,review_state:"unchecked"});
});

test("clean drafts accept live updates and valid timing order is mandatory", () => {
  const current={...cue(),target:{...cue().target,text:"Már itt vagyok."}};
  assert.equal(mergeDraft(newDraft(cue(),1),current,2).values.target_text,"Már itt vagyok.");
  assert.equal(isDirty(newDraft(cue(),1)),false);
  assert.throws(()=>changesFor(changeField(newDraft(cue(),1),"end","00:00:00,999")));
});

test("an agent finishing its phase does not make unreviewed targets exportable", () => {
  const entries=Array.from({length:848},(_,i)=>({...cue(),entry_id:`cue-${i+1}`,ordinal:i+1}));
  for (const ordinal of [304,569,571]) entries[ordinal-1].target={...cue().target,state:"needs_review"};
  const view=targetReadiness(entries,{state:"pending",phase:"finished"},5);
  assert.equal(view.agentFinished,true);
  assert.equal(view.state,"review");
  assert.equal(view.reviewedCount,845);
  assert.deepEqual(view.pending.map(entry=>entry.ordinal),[304,569,571]);
  assert.equal(targetReadiness(entries,null,5,{revision:5,status:"complete",target_ready:true}).state,"review");
});

test("all reviewed targets require current successful server validation", () => {
  const entries=[cue()];
  assert.equal(targetReadiness(entries,{phase:"finished"},7).state,"checking");
  const valid={revision:7,status:"complete",target_ready:true};
  assert.equal(targetReadiness(entries,null,7,valid).state,"ready");
  assert.equal(targetReadiness(entries,null,8,valid).state,"checking");
  assert.equal(targetReadiness(entries,null,7,{...valid,target_ready:undefined}).state,"invalid");
  const issue={code:"invalid_translation_formatting",details:{issues:["Unclosed italic tag"]}};
  const broken={...valid,target_ready:false,issue};
  assert.equal(targetReadiness(entries,null,7,broken).state,"invalid");
  assert.equal(targetReadiness(entries,null,7,broken).issue,issue);
  assert.equal(targetReadiness(entries,null,7,{revision:7,status:"error",issue:{code:"transport_unknown"}}).state,"error");
});

test("only a currently validated ready target plans a final export without confirmation", () => {
  const ready=targetReadiness([cue()],null,7,{revision:7,status:"complete",target_ready:true});
  assert.deepEqual(targetExportPlan(ready,"project-1",7),{projectId:"project-1",revision:7,variant:"target",
    requiresConfirmation:false,pendingCount:0,missingCount:0,validationIssue:null});
  for (const validation of [null,{revision:6,status:"complete",target_ready:true},
    {revision:7,status:"error",issue:{code:"transport_unknown"}}]) {
    assert.equal(targetExportPlan(targetReadiness([cue()],null,7,validation),"project-1",7),null);
  }
});

test("draft confirmation counts missing, unchecked and stale cues without changing review states", () => {
  const ready=cue(), missing={...cue(),entry_id:"cue-2",target:null};
  const unchecked={...cue(),entry_id:"cue-3",target:{...cue().target,review_state:"unchecked"}};
  const stale={...cue(),entry_id:"cue-4",target:{...cue().target,state:"needs_review"}};
  const blank={...cue(),entry_id:"cue-5",target:{...cue().target,text:" \n ",review_state:"unchecked"}};
  const entries=[ready,missing,unchecked,stale,blank], before=structuredClone(entries);
  const plan=targetExportPlan(targetReadiness(entries,{phase:"finished"},8),"project-1",8);
  assert.equal(plan.variant,"draft");
  assert.equal(plan.requiresConfirmation,true);
  assert.equal(plan.pendingCount,4);
  assert.equal(plan.missingCount,2);
  assert.deepEqual(entries,before);
});

test("a final semantic validation issue permits an explicitly confirmed draft", () => {
  const issue={code:"speaker_markers_changed",details:{entry_id:"cue-1"}};
  const view=targetReadiness([cue()],null,8,{revision:8,status:"complete",target_ready:false,issue});
  const plan=targetExportPlan(view,"project-1",8);
  assert.equal(plan.variant,"draft");
  assert.equal(plan.requiresConfirmation,true);
  assert.equal(plan.pendingCount,0);
  assert.deepEqual(plan.validationIssue,issue);
});

test("confirmation remains tied to its project and exact saved revision", () => {
  const plan=targetExportPlan(targetReadiness([{...cue(),target:null}],null,9),"project-1",9);
  assert.equal(exportPlanCurrent(plan,"project-1",9),true);
  assert.equal(exportPlanCurrent(plan,"project-2",9),false);
  assert.equal(exportPlanCurrent(plan,"project-1",10),false);
  assert.equal(exportPlanCurrent(null,"project-1",9),false);
});

test("draft report routes use only UUID requests and can be rebuilt from receipts", () => {
  const id="5b2cfefe-4b44-40b4-b494-c06451dc581b";
  assert.equal(draftReviewDownloadUrl(id),`/ui/download/${id}/review`);
  for (const invalid of [undefined,null,"",`${id}/../../other`,"https://example.com/review","javascript:alert(1)"]) {
    assert.equal(draftReviewDownloadUrl(invalid),null);
  }
});

test("the pending filter includes missing and unreviewed targets with search applied", () => {
  const ready={...cue(),ordinal:1};
  const missing={...cue(),entry_id:"cue-2",ordinal:2,target:null};
  const unchecked={...cue(),entry_id:"cue-3",ordinal:3,target:{...cue().target,review_state:"unchecked"}};
  assert.deepEqual([ready,missing,unchecked].filter(entry=>matchesEntry(entry,"pending")).map(entry=>entry.ordinal),[2,3]);
  assert.equal(matchesEntry(missing,"pending","wait"),true);
  assert.equal(matchesEntry(unchecked,"pending","3"),true);
  assert.equal(matchesEntry(unchecked,"pending","nincs találat"),false);
  assert.equal(matchesEntry(missing,"review"),false);
  assert.equal(matchesEntry(missing,"missing"),true);
});

test("normal in-flight writes stay silent and known rejection clears pending state", () => {
  const pending={args:{request_id:"exact-request-id"},resultState:"in_flight"};
  assert.equal(pendingWarningVisible(pending),false);
  for (const code of ["translation_incomplete","revision_conflict","invalid_translation_formatting","workspace_busy"]) {
    assert.equal(pendingAfterError(pending,code),null);
  }
  assert.equal(pendingWarningVisible(null),false);
});

test("unknown and restored write results warn while preserving the exact retry request", () => {
  const pending={path:"/ui/export",args:{project_id:"project-1",request_id:"exact-request-id"},resultState:"in_flight"};
  for (const code of ["transport_unknown","invalid_api_response","io_error","internal_error","workspace_error","export_write_error",undefined]) {
    const unknown=pendingAfterError(pending,code);
    assert.equal(pendingWarningVisible(unknown),true);
    assert.deepEqual(unknown.args,pending.args);
    assert.equal(unknown.path,pending.path);
  }
  const restored=restorePending(JSON.parse(JSON.stringify(pending)));
  assert.equal(pendingWarningVisible(restored),true);
  assert.deepEqual(restored.args,pending.args);
  assert.equal(restorePending(null),null);
});
