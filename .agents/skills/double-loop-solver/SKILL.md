---
name: double-loop-solver
description: Solve multistep tasks with evidence-based iterations and human review of important choices. Coordinate autonomous implementation workers with user-led operational discovery and optimization, including iterative stakeholder clarification; skip for simple edits.
---

# Double-loop solver

Deliver the requested result under an explicit task contract. Separate improving an implementation from deciding whether the contract needs correction. This is a lightweight workflow, not a correctness guarantee.

Use the current permitted agent and tools. No extra framework, model, external AI/API connection, UI automation, or software upgrade is needed or authorized by this skill. A single agent can diagnose, implement, and verify sequentially. Optional reviewers provide evidence and alternatives; they cannot authorize contract changes. For a substantial authorized unit with independent workstreams, proactively use available parallel agents when the expected benefit exceeds coordination overhead. Read [parallel work](references/parallel-work.md) to split that unit into small worker tasks with one observable result, explicit file ownership, dependencies, shared budget and evidence; it also covers supported model/effort selection and an actual startup capability check. Keep workers inside authorized scope and decision dependencies; a discussion checkpoint need not pause independent implementation. Simple or dependency-heavy work may remain sequential.

Read [START_HERE](../../../START_HERE.md) for this kit's entry points. Use the following templates only where useful, adapting to task-required filenames rather than creating paperwork for its own sake.

## Match the requested collaboration mode

Read [guided collaboration](references/guided-collaboration.md). The default startup explains the actual problem and waits for understanding before design or implementation. That startup request already authorizes the subsequent required E2E implementation: choose the simplest valid approach in the existing environment, explain it briefly, and dispatch ready worker tasks without another routine approval. Main discusses hidden operational needs, objectives and consequential assumptions with the user while workers build and verify. Inspect actual parallel and waiting-state behavior through [parallel work](references/parallel-work.md); do not infer it from model names or promise unobserved background progress.

Read [stakeholder questions](references/stakeholder-questions.md) at startup and after meaningful baseline results or partial replies. Main actively looks for operationally poor outcomes even when stated constraints pass, prepares questions the user can relay, and narrows unanswered parts until the decision is actionable. Distinguish authoritative requirements, confirmed business rules, chosen improvement objectives and provisional assumptions. Discovery is not authority to invent constraints or an undisclosed scoring rubric.

Keep decision explanations easy to follow: observed result, one recommendation and reason, concrete benefits and tradeoffs, then one material user decision at a time. Do not bundle choices or invent questions for routine work; continue independent authorized implementation while dependent decisions wait. The guided reference explains the interaction pattern and distinguishes user decisions from stakeholder question drafts.

After shared understanding, main proactively proposes suitable algorithm or solution approaches when they materially affect quality, runtime or resource use; do not wait for the user to name a method. Ground a short comparison and one recommendation in the actual inputs, constraints and available environment, explain the mechanism and tradeoffs plainly, and ask only the consequential unresolved operational choice. Revisit after initial results or bottlenecks. Follow the guided reference's approach-selection procedure for bounded comparisons, worker handoff and recorded evidence; routine choices remain delegated.

For a concrete method choice, read [method selection](references/method-selection.md) and adapt the [candidate comparison](../../../templates/candidate-comparison.md) to the actual contract. A small [allocation lab](../../../examples/ALLOCATION_LAB.md) demonstrates independent saved-result checking; it is an optional synthetic example, not a mandatory startup step or a solver for arbitrary tasks.

If the user asks for stage-by-stage control, pause at those checkpoints instead. A fully autonomous request may omit the comprehension pause. Preserve the actual requested mode and scope; never infer approval or understanding from silence. Routine commands and worker handoffs inside authorized scope do not need repeated approval.

## Establish the contract

Use [task-contract](../../../templates/task-contract.md) to assign a contract ID and record:

- Required outputs, mandatory constraints, permitted tools, and the authoritative sources behind them.
- Confirmed README requirements, supplied data facts, and stakeholder statements, separately from assumptions and unresolved questions.
- Each rule's source/authority separately from its enforcement: task-mandated constraint, user-added policy or implementation assumption; hard/default/objective status, scope and authorized exceptions. A user-added hard condition remains user-revisable and is not promoted into an immutable task mandate.
- Observable acceptance criteria, protected invariants, and checks with known expected results.
- Whether the deliverable is one result or a reusable/configurable service; permitted operator inputs, parameter domains, autonomous decision policy, fallback and failure behavior. Defaults are not immutable requirements when the task permits changing them.
- The delivery deadline, available time, and a bounded improvement budget.

Preserve authoritative instructions, supplied raw data, and official test expectations. Edit designated starter or implementation files when the task requires it. Derived data, your own tests, and proposed assumptions are separate artifacts. Do not silently relax a check, discard a failing case, or reinterpret a requirement to make progress look better. Respect explicit source precedence. For unresolved conflicts, preserve the evidence and seek clarification rather than inventing a priority rule.

Requirements already settled by authoritative task instructions or an explicit human decision are actionable within the agreed work unit without asking for approval again. The initial understanding checkpoint and any explicitly requested pauses still apply. In two-track mode, routine implementation proceeds within the broader E2E authorization while only decision-dependent changes wait.

For a failing command or feature, use [evidence-debug](../evidence-debug/SKILL.md) within the agreed unit. When recording repeated test runs against changing files, read [local evidence tools](references/evidence-tools.md); use the bundled runner only if it adds useful traceability. For a local web interface or API, read [app checks](references/app-checks.md) when planning the affected verification; distinguish actual HTTP responses, saved state and human preview checks.

For an existing implementation, a negative-path test, a saved/editor/server discrepancy, parallel editing, or final delivery review, read the relevant section of [execution review](references/execution-review.md). Use [question guidance](references/stakeholder-questions.md) proactively for material gaps and observed operational anomalies. A partial stakeholder reply resolves only the parts it actually answers; draft a focused follow-up for the remainder and avoid repeating settled questions.

When improving a candidate for supplied fixed inputs, use [optimization validation](../analysis-validation/references/optimization-validation.md) to measure the baseline and choose evaluation scope. Keep feasibility gates, proxy screening and final full-input checks distinct; do not apply predictive holdout rules to a different objective.

For a new hard condition, user-policy relaxation or scoped exception, unresolved assignments, material scope expansion, experimental candidate or final running/delivery candidate, read [baseline and delivery](references/baseline-and-delivery.md). Use low-cost feasibility checks and a cost-to-delivery estimate before expanding, preserve a rebuildable candidate with its contract, and connect the actual delivered snapshot to its execution and results. These are technical checks inside the agreed unit, not extra approvals for every command. For configurable services, human decisions establish the general policy during development; normal runtime recomputation selects cases and applies that policy automatically. Read the same reference for dynamic exception eligibility, policy/input/settings versions, current-parameter validation and bounded recovery. Do not deliver a one-off manually repaired answer in place of the required service.

## Inner loop: improve under the same contract

Use [cycle-log](../../../templates/cycle-log.md) to keep each iteration small:

1. Capture the failure, the expected behavior, and observed evidence. Classify the likely cause before editing.
2. State one failure hypothesis and choose one primary change target: implementation, working instructions you authored, an example, or your own verification code.
3. Execute the smallest useful change. Run the relevant checks and regression cases that previously passed. Record exact commands, results, and what remains untested.
4. Compare against the best saved candidate under the same contract ID. Mandatory gates and protected invariants come before any pass count. Preserve a reproducible snapshot and revert regressions when appropriate.

An agent's confidence, self-assigned score, or claim of completion is not correctness evidence. Ground expected values in source material, calculations, or confirmed requirements. Distinguish a broken implementation from a mistaken local oracle; a material correction to that oracle belongs in the outer loop.

## Outer loop: review the contract

Escalate material uncertainty about meaning, scope, success criteria, conflicting evidence, or architectural commitments that determine supported behavior. Also review repeated non-improvement, exhausted budgets, and proposals that trade away a mandatory requirement. Ordinary refactoring does not require escalation.

A partial or worse candidate is not necessarily a dead end. Preserve promising experiments separately from the valid incumbent, distinguish rule conflicts from limited search, and explore small repairs by changing only user-added policies within the budget. Show affected subjects, scope, expected versus observed recovery and tradeoffs; apply an existing delegated adjustment range or obtain the user's decision before adopting a material change. A subject-triggered exception may apply to its whole assigned group: recompute eligibility from final membership after reassignment and verify all exceptions jointly. Task-mandated requirements remain protected. Once an authorized exception is part of the new contract and all remaining requirements pass, the candidate may become a valid deliverable; it is not permanently experimental merely because a user policy changed.

Use [outer-review](../../../templates/outer-review.md) for a short decision packet: current contract ID, failure evidence, conflicting sources, realistic options, tradeoffs, and a recommended choice. Ask the authorized human to decide when the available instructions do not settle the issue. Keep independent work running within the authorized implementation scope while the dependent choice waits. In two-track mode, main explicitly sends the new contract version, changed rule, affected interfaces and acceptance evidence to affected workers; reconcile stale results before integration. Honor a user-requested whole-work pause. Do not treat silence, a reviewer recommendation, or an AI-generated approval as a human decision.

Record the actual decision and its source. If the contract changes, issue a new ID, update your derived checks with reasons, and rebaseline the candidate. Scores from different contracts are not directly comparable. Revalidate affected behavior and previously protected cases before resuming refinement.

## Stop and deliver

Choose finite iteration and time limits before repeated refinement. Two consecutive attempts without meaningful improvement can be an adjustable starting proposal for human review, not a universal rule. Stop improving when mandatory criteria pass and remaining work has low value, or the agreed budget requires finalization.

For a time-limited task, agree on a delivery-check buffer within the actual allocated time. Follow the task's real deadline and required later stages. Use supplied remaining time, a known deadline, or a permitted reliable clock; do not use UI automation to read the timer or claim automatic timer access or hard enforcement.

Restore the strongest candidate for the active contract, verify required files and saved state, and summarize decisions, executed evidence, and unresolved limitations. Explain what was confirmed and what remains assumed. Review key choices, evidence, and limits with the user during the permitted task-work phase; follow the guided reference for a requested [full solution review](../../../templates/solution-review.md), separate practice Q&A, comprehension, and workflow handoff. Keep delivery and human understanding ahead of another speculative iteration.
