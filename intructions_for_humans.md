# DataSpeakAI — Reusable Prompts for Humans Working with AI Agents

Created: 2026-10-16. Use this guide from the DataSpeakAI project folder. Replace bracketed placeholders before sending a prompt. Each prompt is designed to be pasted into a fresh agent session.

The normal workflow is:

**Select a phase → plan it in todo.md → implement ready tasks → commit locally → independently review the committed work → fix confirmed findings → verify the fixes → check phase completion.**

The planning and implementation sessions can be in different windows. They must use the same updated project files, or a branch containing the saved plan. Finish one session's edits to shared tracking files before another session edits them.

## 1. Project references and basic rules

| File | What it is for |
|---|---|
| [AGENTS.md](AGENTS.md) | Engineering rules, Graft usage, verification, and record maintenance |
| [todo.md](todo.md) | Selected phase, milestones, sprints, task dependencies, and completion archive |
| [Next release pathway](docs/next_release_implementation_pathway.md) | Release design, issue and feature IDs, implementation steps, and exit criteria |
| [CHANGELOG.md](CHANGELOG.md) | Recorded changes; verify claims against current code and test evidence |
| [Session notes](docs/sessions/README.md) | How project sessions and architectural handoffs are recorded |
| [Task dispatch template](docs/templates/AI_TASK_TEMPLATE.md) | Ownership and context when work is assigned to another agent or developer |

- **Release labels:** NR1 contains phases NR-0 through NR-3; NR2 contains NR-4; NR3 contains NR-5. There is currently no NR-6. Historical Phase 6/7 records are a separate naming scheme.
- **Planning order:** Normally NR-0 → NR-1 → NR-2 → NR-3 → NR-4 → NR-5. Explicit dependencies can require a prerequisite from a later phase first. The pathway's section 14 explains these relationships.
- **Checkbox meaning:** An unchecked task is unfinished. Its dependency evidence determines whether it is ready. Checked tasks belong in the completion archive and must have verification evidence.
- **Preserve history:** Add new plans and corrective records without rewriting old completion reports. A QA finding can create a linked repair task and change current readiness without deleting the historical record.
- **Graft first:** Ask the agent to use `graft map`, `graft ask`, and exact source spans. If Graft is unavailable or stale, it should state that and verify against source instead of inventing graph results.
- **Scope is explicit:** Planning prompts edit the tracker; implementation and repair prompts authorize scoped code changes; review prompts report findings. The commit prompt authorizes a local commit. None of these prompts requests a push or deployment.
- **Evidence matters:** A test run that was skipped, failed to start, or used only mocks is not evidence that the corresponding live integration passed.

This guide is a prompt library. It does not activate a phase, assign an agent, or execute the instructions inside the examples by itself.

## 2. Choose the prompt you need

| Prompt | Use it when | Expected changes |
|---|---|---|
| [P01 — Understand the current state](#p01) | Starting a fresh session | Read-only report |
| [P02 — Plan a whole phase](#p02) | Mapping a selected phase into the tracker | Only todo.md |
| [P03 — Review the plan](#p03) | Checking whether the mapped phase is executable | Read-only report |
| [P04 — Implement a whole phase](#p04) | Letting an agent work through all ready tasks | Scoped code, tests, and required records |
| [P05 — Implement one milestone or sprint](#p05) | Wanting a smaller implementation boundary | Scoped code, tests, and required records |
| [P06 — Resume in a new session](#p06) | Continuing interrupted work | Remaining authorized work and records |
| [P07 — Investigate blocked tasks](#p07) | Tasks cannot proceed | Read-only diagnosis |
| [P08 — Commit completed work locally](#p08) | Preparing a stable QA review target | Local Git commit of selected changes |
| [P09 — QA review after a local commit](#p09) | Independently checking a milestone or phase | Read-only findings and proposed fixes |
| [P10 — Turn QA findings into repair tasks](#p10) | Preparing a repair implementation session | Only todo.md |
| [P11 — Implement confirmed repairs](#p11) | Fixing findings from a QA report | Scoped fixes, tests, and required records |
| [P12 — Verify the repairs](#p12) | Checking that fixes work and did not regress behavior | Read-only verification report |
| [P13 — Check phase or release readiness](#p13) | Deciding whether to advance | Read-only readiness report |
| [P14 — Prepare a session handoff](#p14) | Moving implementation to another session | Scoped agent handoff/progress metadata |
| [P15 — Investigate a reported bug](#p15) | A user sees unexpected behavior | Read-only reproduction and diagnosis |
| [P16 — Assess a new feature](#p16) | Considering work outside the current plan | Read-only proposal |

For the workflow discussed in this project, start with **P02**, use **P04** in the implementation session, then **P08** if the work has not already been committed. Run **P09** in a fresh QA session. If it finds issues, use **P10 → P11 → P12**. Run **P13** before moving to the next phase or declaring a release ready.

## 3. Placeholders and review boundaries

| Placeholder | Replace it with |
|---|---|
| `[PHASE ID]` | An exact phase such as `NR-0` |
| `[SCOPE ID]` | A phase, milestone, or sprint such as `NR-0`, `NR-0.1`, or `NR-0.1-A` |
| `[TASK IDS]` | Exact tracker IDs, including any explicitly mapped prerequisites |
| `[BASE REF]` | The commit immediately before the selected work began, or `AUTO-DETECT` |
| `[HEAD REF]` | The last local commit containing the selected work; often `HEAD` |
| `[REVIEW ID]` | A unique review label, for example `QA-NR-0.1-20261016-01` |
| `[QA REPORT]` | The complete review output pasted into the prompt, or a real saved report path |
| `[FINDING IDS]` | Selected finding IDs from that review, or `ALL CONFIRMED IN-SCOPE FINDINGS` |
| `[RELEASE ID]` | `NR1`, `NR2`, or `NR3` |

**A milestone can span several commits.** Reviewing only the last commit can miss most of its implementation. Ask the reviewer to resolve the base and head to actual commit hashes and list the reviewed commits. In an ordinary linear history, the base is the parent of the first implementation commit. A merge or an initial repository commit needs an explicitly described comparison; do not blindly assume `HEAD~1` is the right baseline.

If the range contains unrelated work, the reviewer should list it and explain its relevance. It should check each selected commit as well as the combined before/after change and affected callers. A commit message or the implementation agent's final response is context, not proof of correctness.

If the working directory has uncommitted edits, tests run there may not test the committed revision. The QA prompts require an isolated checkout or another method that proves which revision was tested. The reviewer must preserve ongoing work and report any limitation. Do not discard changes to make a review appear clean.

<a id="p01"></a>
## P01 — Understand the current project state

Use this when opening the project in a new tool or session.

```text
Inspect this DataSpeakAI repository and tell me where development currently stands. Read AGENTS.md, todo.md including the archive, CHANGELOG.md, relevant session notes, and docs/next_release_implementation_pathway.md. Use Graft before broad source searches, then verify relevant claims against actual source code.

Report the current branch/revision and existing working-tree changes; the selected release, phase, milestone, and sprint if any; ready and blocked tasks; outstanding QA findings; and the next sensible action with its task ID. Distinguish historical completion claims from behavior verified now. Do not assume an old progress file means another agent is still active.

This is a read-only orientation. Do not modify files, mark tasks complete, commit, or start implementation. If no phase has been mapped, say so rather than choosing one for me.
```

<a id="p02"></a>
## P02 — Convert a whole phase into todo.md

Use this in the planning session. It maps the phase without implementing the application.

```text
Convert Phase [PHASE ID] from docs/next_release_implementation_pathway.md into an actionable plan in todo.md. Read AGENTS.md, the existing tracker and archive, CHANGELOG.md, and relevant session notes. Verify the current implementation using Graft and relevant source code.

Use the new selected-phase work area and the existing Phase → Milestones → Sprints → Tasks format. Preserve exact milestone, sprint, and task IDs. Include implementation steps, target components, explicit dependencies, acceptance criteria, verification requirements, and any migration, rollout, or recovery requirements. Record the planning baseline revision and working directory. Make the plan usable by another session without this chat.

Identify and explicitly map any prerequisites from other phases, retaining their original IDs and explaining why they are needed. Use the pathway section 14 crosswalk to link overlapping legacy tasks. Keep one implementation lineage. Check for duplicate IDs, missing prerequisites, circular dependencies, and shared-file ownership conflicts. Do not invent completion evidence for work that merely appears similar to an archived task.

Preserve unrelated pending tasks, previous phase summaries, and all completion history. Only edit todo.md; do not implement application code or update other records in this planning session. Report what was mapped, the first ready task, and any unresolved planning blockers.
```

<a id="p03"></a>
## P03 — Review the mapped plan before execution

Use this when you want a second check of the plan.

```text
Review the plan for [PHASE ID] in todo.md against docs/next_release_implementation_pathway.md. Read AGENTS.md, inspect the current revision and working-tree changes, and use Graft and source code to check implementation assumptions.

Verify that every in-scope pathway task is represented or has an evidence-backed explanation; IDs are stable; prerequisites resolve to tasks or verifiable contract gates; no dependency cycles exist; cross-phase prerequisites are explicit; legacy work is linked without duplicate ownership; and acceptance criteria, verification, migrations, and recovery steps are executable. Check that another session can identify the next ready task without reading this conversation.

Report actionable planning defects, missing decisions, and the proposed correction for each. State whether the plan is ready for implementation and list the first ready tasks. Do not edit files, implement code, or mark tasks complete.
```

<a id="p04"></a>
## P04 — Implement the selected phase step by step

Use this in the implementation window after planning is finished.

```text
Read AGENTS.md and implement the selected phase in todo.md step by step. Also read its section in docs/next_release_implementation_pathway.md, CHANGELOG.md, and relevant session notes. Inspect the current branch, revision, and existing changes. Use Graft and current source before editing; preserve other people's work.

Work on tasks whose dependencies are completed and verified, including explicitly mapped cross-phase prerequisites. Among ready tasks, follow priority and the planned milestone/sprint order. Skip blocked tasks, continue with ready tasks, and revisit dependent tasks as prerequisites finish. Stay within the selected phase and its mapped prerequisites. If no phase is mapped, report that instead of selecting unrelated backlog work.

Claim ownership before editing shared files. Implement concrete behavior, not placeholders or fabricated success. Verify each task against its acceptance criteria and required checks, including relevant failure cases and integration behavior. Use isolated test databases, indexes, and configuration; do not run startup or migrations against real project data merely to test imports.

Keep incomplete or unverified tasks unchecked. After verified completion, archive the entire task block with its ID and evidence, and maintain required progress, handoff, changelog, and documentation records under the repository rules. Preserve historical records. Do not silently broaden the phase when a new issue is discovered; record its dependency impact.

Continue until the phase and its exit checks are complete or no remaining task can proceed. Report completed task IDs, actual verification results, blockers, and the next ready task. Record the starting commit so the full implementation can be reviewed later. Do not commit, push, or deploy unless I separately request it.
```

<a id="p05"></a>
## P05 — Implement one milestone or sprint

Use this instead of P04 when you want a smaller stopping point.

```text
Implement only [SCOPE ID] from todo.md. Read AGENTS.md, the selected-phase metadata, its pathway requirements, CHANGELOG.md, and relevant session notes. Inspect existing changes and use Graft plus current source to verify targets and prerequisites.

Work through this scope's ready tasks in dependency order. Include only prerequisites already explicitly mapped for this scope; report any additional prerequisite that needs planning. Preserve unrelated work and coordinate shared-file ownership. Run the task acceptance checks and required repository verification, using isolated test data. Revisit blocked tasks as prerequisites finish.

Archive verified task blocks and update required implementation records without rewriting historical reports. Keep unfinished work unchecked. Stop when this milestone or sprint is complete, or all remaining work in this scope is blocked; do not automatically advance to the next milestone.

Report task IDs, changes, verification evidence, remaining blockers, and the starting and ending revision/worktree state for later QA. Do not commit, push, or deploy.
```

<a id="p06"></a>
## P06 — Resume implementation in another session

Use this after a session ends, the tool changes, or the agent loses context.

```text
Resume the selected phase in todo.md. Read AGENTS.md, the active plan and archive, the corresponding pathway section, CHANGELOG.md, and the latest relevant handoff/progress notes. Inspect the current branch, revision, and staged, unstaged, and untracked changes before editing. Use Graft and current source to verify the state.

Determine which tasks are verified complete, which have partial changes, and which are blocked. Do not redo completed work or discard partial work. Recheck stale ownership and coordinate before taking over files. If a partially implemented task lacks verification, finish that verification before claiming completion.

Continue with ready tasks within the existing phase scope, revisiting dependencies as work finishes. Follow the same acceptance, isolated-test, archival, and record-maintenance rules as AGENTS.md and todo.md. Report your recovered state briefly, then continue until the phase is complete or no remaining task can proceed. Do not commit, push, or deploy.
```

<a id="p07"></a>
## P07 — Diagnose blocked tasks

Use this when progress stops and you want an explanation before changing the plan.

```text
Investigate why tasks [TASK IDS] in todo.md are blocked. Read AGENTS.md, their pathway requirements, dependency records, relevant archive entries, and current source using Graft.

For each task, identify the exact missing prerequisite, failed check, environment limitation, or unresolved decision. Verify whether its dependency was completed elsewhere, whether the blocker is stale, or whether a cycle exists. List other tasks that can still proceed and propose the smallest ordered steps that would unblock the affected work.

Separate code defects from missing tools/services and planning gaps. Do not edit files, install dependencies, change credentials, mark tasks complete, or implement a workaround that bypasses a required control. Return a concrete diagnosis and suggested tracker updates.
```

<a id="p08"></a>
## P08 — Commit completed work locally for QA

Use this only when you want the agent to create a local commit. Skip it if the implementation has already been committed.

```text
Create a local Git commit for the completed work in [SCOPE ID] from todo.md. Read AGENTS.md and the relevant task and verification records. Inspect the current branch, staged changes, unstaged changes, and untracked files. Identify the exact files and hunks belonging to this scope, including required tests and documentation.

Review the changes and existing verification evidence. Run any missing checks required for these changes using isolated test data. Do not claim a scope is complete if its acceptance checks fail or are unavailable. Preserve unrelated work and any existing staged changes; if you cannot separate the intended scope safely, explain the exact ambiguity before committing.

Stage only the relevant changes. Exclude secrets, local databases, uploaded documents, generated indexes, and unrelated artifacts. Review the staged diff and create a descriptive local commit referencing the relevant task IDs. Do not amend existing commits, rewrite history, push, or deploy.

Return the new commit hash, included files/tasks, actual verification results, remaining working-tree changes, and the base and head refs recommended for reviewing the whole milestone or phase. If the scope spans earlier commits, include them in the recommended QA range rather than reporting only the new commit.
```

<a id="p09"></a>
## P09 — Independent QA review after a milestone or phase was committed

**This is the main prompt to run after an implementation agent commits work locally.** Prefer a fresh session so the review starts from the repository evidence. The agent finds issues and proposes repairs; P10 and P11 handle recording and implementing them.

If you do not know the starting commit, replace `[BASE REF]` with `AUTO-DETECT`. For the latest committed state, replace `[HEAD REF]` with `HEAD`. Give the exact milestone or phase ID whenever possible. Attach the previous agent's summary if available, but the reviewer must verify it.

```text
Act as an independent senior QA engineer and code reviewer for DataSpeakAI. An agent has implemented and locally committed the following scope. Review the actual implementation, find current defects and credible future failure cases caused by these changes, and explain the fixes needed.

Scope: [SCOPE ID]
Review ID: [REVIEW ID]
Base ref: [BASE REF]
Head ref: [HEAD REF]
Implementation summary or original request: [PASTE IF AVAILABLE; OTHERWISE USE THE TRACKER AND PATHWAY]

1. Establish the review target.
Read AGENTS.md, todo.md including archived task blocks, CHANGELOG.md, the relevant section of docs/next_release_implementation_pathway.md, and relevant handoffs. Inspect Git status and history. Resolve base and head to exact hashes, list the reviewed commits, and explain the selected comparison. If the base is AUTO-DETECT, use task IDs, the recorded implementation baseline, changed files, and commit history to identify the full scope. Do not assume the last commit contains the entire milestone. Account explicitly for merges or an initial commit. If the complete boundary is ambiguous, state the limitation and review the confirmed portion without claiming full milestone coverage.

2. Keep the evidence tied to that revision.
Record staged, unstaged, and untracked changes separately from committed work. Do not reset, stash, overwrite, or mix another agent's pending edits into the committed review. If the checkout differs from the reviewed head, use an isolated review checkout or a verified equivalent method for testing that head. Record the tested revision and environment. If this is unavailable, label the affected checks unverified. Graft may describe the current checkout, so validate its source pointers against the reviewed revision.

3. Inspect implementation and affected behavior.
Use Graft for orientation and caller/dependency tracing, then read every changed first-party source/configuration/test file and relevant definitions in full. Review both the combined change and individual commits where needed. Inspect affected callers, authorization boundaries, schemas, clients, migrations, and error paths beyond the diff. Assess manifests and lockfile changes for compatibility; inspect generated/binary artifacts through their source and reproducible build or appropriate inspection. Do not treat comments, passing tests, TODO checkboxes, mock responses, or the previous agent's claims as proof that behavior is correct. State any files or paths you could not inspect.

4. Check the promised behavior and regression risks.
Map each in-scope task's acceptance criteria to implementation and verification evidence. Cover relevant success and failure cases: tenant isolation; platform versus tenant roles; creator-only conversation privacy; widget session ownership and published-source scope; SQL/NoSQL read safety; host/path validation; secrets; row caps and actual cancellation; API/model/frontend consistency; persistence and migration compatibility; metric correctness and ML leakage; grounding and retrieval lifecycle; stream cancellation and duplicate generation; retries, concurrency, quotas, and resource cleanup. Apply the checks relevant to the change and explain significant exclusions instead of mechanically claiming every area was tested.

5. Verify with meaningful checks.
Inspect available scripts and tests, then run the checks required by AGENTS.md and the task's acceptance criteria, including targeted regression cases and relevant build, backend, type, integration, and UI checks. Compare a suspected regression with the base revision when feasible. Use disposable databases, indexes, uploads, and configuration; inspect startup/migration effects before importing the application. Do not modify real project data, use live customer connections, or accidentally trigger real email, billing, or paid-provider calls. Distinguish mocked checks from live integration checks. Do not install or upgrade packages merely to make the environment match without explaining the need. Do not weaken tests or change application code during this review. Temporary reproductions may run in an isolated disposable location, with results reported in the response.

6. Produce an actionable QA report.
Use stable finding IDs within this Review ID, such as F01 and F02. Order findings by practical severity: P0 critical exposure or destructive failure, P1 major correctness/security/reliability failure, P2 material but bounded defect, P3 minor actionable defect. Set severity from the actual trigger and impact, not the label of the component.

For every finding include:
- Finding ID, severity, and concise title.
- Whether it was introduced by the reviewed changes, is an unmet in-scope requirement, or predates the change. Label uncertain attribution explicitly.
- Exact file and line at the reviewed revision, affected task ID, and relevant code path.
- Trigger and reproducible steps or direct code evidence; expected versus actual behavior.
- Impact, underlying reason, and the smallest suitable fix in ordered steps.
- A regression check that would demonstrate the fix.

Separate confirmed defects from hypotheses needing verification and from optional enhancements. Future-risk findings need a concrete plausible trigger and supported failure path. Do not manufacture findings or inflate style preferences into defects. If no actionable findings are found, say so and still describe the coverage limits.

End with: (a) exact commit range and tested revision; (b) acceptance-criteria coverage with verified, failed, or unverified status; (c) commands and actual results, including skips and failures; (d) ordered repair recommendations and dependencies; and (e) a readiness verdict: verified within the stated scope, changes required, or verification blocked. Explain any remaining uncertainty. An unrelated pre-existing defect should be reported separately, not falsely attributed to this implementation.

This is an audit, not a repair session. Do not edit source, tests, todo.md, CHANGELOG.md, or other project records; do not commit, push, or deploy. Return the complete report in your response so I can pass it to a planning or repair agent.
```

## 4. How to use the QA result

Keep the review ID, reviewed commit hashes, finding IDs, reproduction steps, and verification limitations together when transferring the report. A new agent cannot reliably act on “fix what the other window found” without that context.

Use P10 to create repair tasks, P11 to implement them, and P12 to independently verify them. If you want a saved QA report, explicitly request a report file in `docs/reports/`; an agent handoff belongs under `.agents/`. Do not silently overwrite an old report with a new review.

<a id="p10"></a>
## P10 — Convert confirmed QA findings into todo.md repair tasks

Use this to prepare repairs while retaining the original implementation history.

```text
Convert the confirmed in-scope findings from the QA report below into actionable repair tasks in todo.md.

Scope: [SCOPE ID]
Review ID: [REVIEW ID]
QA report or saved report path: [QA REPORT]

Read AGENTS.md, the existing tracker and archive, and the relevant pathway requirements. Verify each finding against current source using Graft; the implementation may have changed since the reviewed commit. Record the reviewed revision and current baseline. Do not create repair tasks for a claim already disproved or fixed without explaining the evidence.

Add a clearly labeled QA repair milestone under the affected phase. Use unique IDs derived from the review ID and finding ID, such as QA-NR-0.1-20261016-01-F01. These are tracker repair IDs, not new pathway IDs. Link each task to the original roadmap task and its review finding. Include reproduction, root cause, implementation steps, dependencies, target files, acceptance criteria, and regression verification. Recheck duplicate findings and dependency cycles. Map cross-phase work explicitly if it is required.

Preserve all historical completion entries and unrelated pending tasks. Add a current readiness note explaining any confirmed blocker instead of rewriting an old completion claim. Keep unconfirmed hypotheses as investigation items and optional enhancements separate from required repairs.

Only edit todo.md. Do not implement code, change other records, commit, push, or deploy. Report the mapped repair IDs, priority order, and first ready repair task.
```

<a id="p11"></a>
## P11 — Implement the confirmed QA repairs

Use this after P10 has mapped the repair tasks.

```text
Implement the mapped QA repair tasks for [SCOPE ID] in todo.md.

Review ID: [REVIEW ID]
Findings to repair: [FINDING IDS]
QA report or saved report path: [QA REPORT]

Read AGENTS.md, the repair tasks, linked original tasks and pathway requirements, CHANGELOG.md, and relevant handoffs. Inspect current changes and use Graft plus source to confirm each issue still exists before editing. If a finding is stale or incorrect, explain the evidence and record its disposition without making an unnecessary change.

Work in dependency and severity order. Implement the smallest complete fix for each confirmed issue, preserve unrelated work, and add meaningful regression coverage for the reported trigger. Verify the fix against the original reproduction and affected callers, including relevant failure, permission, migration, concurrency, and client-contract cases. Use isolated test data and run the applicable repository checks.

Keep repairs unchecked until their acceptance and verification requirements pass. Archive complete repair blocks with finding IDs and evidence. Maintain required implementation records while preserving the earlier historical reports. Record newly discovered issues and their impact without silently broadening the repair scope.

Report each finding as fixed and verified, still open, disproved with evidence, or verification blocked. Include actual test results and remaining risks. Continue through the ready mapped repairs; do not commit, push, or deploy unless separately requested.
```

<a id="p12"></a>
## P12 — Independently verify the repairs

Use a fresh QA session where practical. You can verify committed fixes or explicitly identified uncommitted fixes; state which.

```text
Independently verify the fixes for QA review [REVIEW ID] affecting [SCOPE ID].

Original QA report: [QA REPORT]
Fix revision or explicit worktree scope: [FIX COMMIT/RANGE, OR CURRENT UNCOMMITTED REPAIR TASK IDS]

Read AGENTS.md, the original findings, repair task records and archive, the relevant pathway criteria, and current Git status/history. Use Graft and source to inspect the fixes and affected callers. Identify exactly which revision or uncommitted diff is being tested. Preserve unrelated changes; use an isolated checkout for a committed target when the current checkout differs.

Re-run each original reproduction where feasible and verify the intended correction, not just the newly added test. Check that tests would detect the original failure and have not weakened the requirement. Test relevant nearby failure cases and integration behavior for regressions. Use disposable data and run required checks; distinguish actual passes from skips, mocks, unavailable services, and incomplete verification.

Report each original finding as fixed and verified, still reproducible, disproved with evidence, or unverified. List any new actionable findings with file/line, trigger, impact, minimal fix, and regression check. State whether the repair is ready within the verified scope and whether outstanding findings still block the milestone or phase.

Do not edit project files or completion records, commit, push, or deploy. Return a report that can be used to update task readiness in a separate implementation or tracking session.
```

<a id="p13"></a>
## P13 — Check phase or release readiness

Use this before selecting the next phase or calling a release ready. A completed task list alone is insufficient.

```text
Assess readiness for [PHASE ID OR RELEASE ID] using AGENTS.md, todo.md and its archive, docs/next_release_implementation_pathway.md, CHANGELOG.md, relevant handoffs, and the available QA reports: [REPORTS OR NONE AVAILABLE].

Inspect the current revision and changes, and verify code and acceptance evidence using Graft and relevant source. For a release, include all phases required by that release. Check task completion, cross-phase contract dependencies, unresolved QA repairs, integration behavior, migrations/backfills, deployment configuration, restore/rollback evidence, documentation, and the pathway's exit criteria. Run applicable missing verification in an isolated environment where available; report unavailable checks explicitly.

Return a criterion-by-criterion table showing the evidence and verified, failed, or unverified status. Distinguish implementation completion, QA verification, operational readiness, and actual deployment. List concrete blockers and the task IDs needed to resolve them. Recommend advancing only when the required gates are supported by evidence.

This is a read-only readiness assessment. Do not change task states, release versions, configuration, or project records. Do not commit, publish, push, or deploy.
```

<a id="p14"></a>
## P14 — Prepare a handoff for another session

Use this while the implementation session still has useful context.

```text
Prepare a self-contained handoff for the current selected phase in todo.md. Read AGENTS.md and inspect the latest tracker, source changes, and Git state so the handoff reflects actual work.

Create or update only this session's own handoff.md and progress.md under .agents/[AGENT ID]/. Do not overwrite another agent's metadata. Use the five components Observation, Logic Chain, Caveats, Conclusion, and Verification Method.

Include the phase/milestone/sprint and task IDs; repository path, branch/worktree and revision; starting baseline for later QA; owned and changed files; completed and partially implemented work; commands and actual test results; blockers and dependencies; relevant QA findings; decisions and remaining uncertainty; and the exact next ready task. Identify uncommitted work and whether another agent owns shared files. Do not include credentials or private data.

Do not implement additional features, edit product code or historical records, or create a commit. Return the handoff path and a short continuation prompt the next session can use.
```

<a id="p15"></a>
## P15 — Investigate a reported bug before planning its fix

Use this when the problem comes from a real observation rather than a planned task.

```text
Investigate this DataSpeakAI bug: [EXPECTED BEHAVIOR, ACTUAL BEHAVIOR, AND REPRODUCTION STEPS]. Relevant environment or error output: [DETAILS WITHOUT SECRETS].

Read AGENTS.md, inspect Git state and relevant task/session records, and use Graft to locate the affected code and callers. Reproduce the issue with disposable test data where possible. Trace the actual failure path and distinguish the root cause from secondary symptoms. Check whether the behavior is already covered by a pathway issue or an existing repair task.

Report evidence with file/line references, expected versus actual behavior, user impact, root cause, minimal ordered fix steps, affected interfaces, and the regression checks needed. Separate confirmed facts from hypotheses and report anything you could not verify.

Do not modify project files, mark tasks complete, commit, or deploy. Return a diagnosis that can be converted into a scoped todo.md repair task.
```

<a id="p16"></a>
## P16 — Assess an additional feature without expanding active work

Use this when you have a new idea and want to understand its cost and dependencies first.

```text
Assess this proposed DataSpeakAI feature: [FEATURE AND USER PROBLEM]. Read AGENTS.md, todo.md, and docs/next_release_implementation_pathway.md. Use Graft and source to identify existing reusable behavior and constraints.

Explain what is already implemented, what is missing, and whether the feature is already included in the pathway. Propose the smallest useful version, its user flow, required API/data/frontend changes, permission rules, dependencies, migration and operational implications, acceptance criteria, and a milestone/sprint/task breakdown. Explain where it could fit without weakening the current release gates. Identify decisions that materially affect scope.

This is a read-only proposal. Do not insert the feature into the active phase, edit the tracker or pathway, implement code, commit, or deploy. Do not present rough effort estimates as guaranteed delivery dates.
```

## 5. What a useful final agent response should contain

For implementation, expect task IDs, a concise explanation of the delivered behavior, actual verification results, unresolved blockers, and where the work can resume. For a commit, expect the commit hash and the full scope's recommended review range. For QA, expect evidence and a clear verdict rather than a general statement that everything looks good.

If the agent cannot run a required check, it should say what was unavailable and how that limits confidence. If QA finds no defects, it should say “no actionable findings within the reviewed scope” and identify what was actually reviewed and tested. Neither a checklist nor a successful build proves that every runtime behavior is correct.

The human selects the scope and decides when to advance. The tracker carries the implementation order, the source establishes actual behavior, and verification evidence supports completion.
