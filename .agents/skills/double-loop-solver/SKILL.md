---
name: double-loop-solver
description: Solve multistep tasks with evidence-based iterations and human review of important choices. Support guided collaboration when the user wants to understand and direct the work; skip for simple edits.
---

# Double-loop solver

Deliver the requested result under an explicit task contract. Separate improving an implementation from deciding whether the contract needs correction. This is a lightweight workflow, not a correctness guarantee.

Use the current permitted agent and tools. No extra framework, model, external AI/API connection, UI automation, or software upgrade is needed or authorized by this skill. A single agent can diagnose, implement, and verify sequentially. Optional reviewers provide evidence and alternatives; they cannot authorize contract changes. For a substantial authorized unit with independent workstreams, proactively use available parallel agents when the expected benefit exceeds coordination overhead. Read [parallel work](references/parallel-work.md) to split that unit into small worker tasks with one observable result, explicit file ownership, dependencies, shared budget and evidence; it also covers supported model/effort selection and fallbacks. Keep every worker inside the current unit and real human checkpoints; simple or dependency-heavy work may remain sequential.

Read [START_HERE](../../../START_HERE.md) for this kit's entry points. Use the following templates only where useful, adapting to task-required filenames rather than creating paperwork for its own sake.

## Match the requested collaboration mode

For the kit's default startup, or when the user wants to learn, understand, or direct the work, read [guided collaboration](references/guided-collaboration.md). First explain the actual problem and wait for the user's understanding confirmation before solution design or implementation. Then agree on an approach and meaningful work unit; explain progress even without a decision and pause at the agreed checkpoints. No background solver may bypass those pauses.

For a user-authorized autonomous workflow, follow the same contract and evidence requirements with concise progress updates and material human decisions. Do not switch modes, broaden a work unit, or mark comprehension as confirmed without the user's actual direction. Routine commands inside an agreed unit do not require repeated approval.

## Establish the contract

Use [task-contract](../../../templates/task-contract.md) to assign a contract ID and record:

- Required outputs, mandatory constraints, permitted tools, and the authoritative sources behind them.
- Confirmed README requirements, supplied data facts, and stakeholder statements, separately from assumptions and unresolved questions.
- Observable acceptance criteria, protected invariants, and checks with known expected results.
- The delivery deadline, available time, and a bounded improvement budget.

Preserve authoritative instructions, supplied raw data, and official test expectations. Edit designated starter or implementation files when the task requires it. Derived data, your own tests, and proposed assumptions are separate artifacts. Do not silently relax a check, discard a failing case, or reinterpret a requirement to make progress look better. Respect explicit source precedence. For unresolved conflicts, preserve the evidence and seek clarification rather than inventing a priority rule.

Requirements already settled by authoritative task instructions or an explicit human decision are actionable within the agreed work unit without asking for approval again. Guided-mode understanding and progression checkpoints still apply; routine implementation choices inside that unit remain within scope.

For a failing command or feature, use [evidence-debug](../evidence-debug/SKILL.md) within the agreed unit. When recording repeated test runs against changing files, read [local evidence tools](references/evidence-tools.md); use the bundled runner only if it adds useful traceability. For a local web interface or API, read [app checks](references/app-checks.md) when planning the affected verification; distinguish actual HTTP responses, saved state and human preview checks.

For an existing implementation, a negative-path test, a saved/editor/server discrepancy, parallel editing, or final delivery review, read the relevant section of [execution review](references/execution-review.md). When the user asks to refine stakeholder questions, use [question guidance](references/stakeholder-questions.md) without inventing new topics or repeating answered parts.

When improving a candidate for supplied fixed inputs, use [optimization validation](../analysis-validation/references/optimization-validation.md) to measure the baseline and choose evaluation scope. Keep feasibility gates, proxy screening and final full-input checks distinct; do not apply predictive holdout rules to a different objective.

For a new hard condition, material scope expansion, experimental candidate or final running/delivery candidate, read [baseline and delivery](references/baseline-and-delivery.md). Use low-cost feasibility checks and a cost-to-delivery estimate before expanding, preserve a rebuildable candidate with its contract, and connect the actual delivered snapshot to its execution and results. These are technical checks inside the agreed unit, not extra approvals for every command.

## Inner loop: improve under the same contract

Use [cycle-log](../../../templates/cycle-log.md) to keep each iteration small:

1. Capture the failure, the expected behavior, and observed evidence. Classify the likely cause before editing.
2. State one failure hypothesis and choose one primary change target: implementation, working instructions you authored, an example, or your own verification code.
3. Execute the smallest useful change. Run the relevant checks and regression cases that previously passed. Record exact commands, results, and what remains untested.
4. Compare against the best saved candidate under the same contract ID. Mandatory gates and protected invariants come before any pass count. Preserve a reproducible snapshot and revert regressions when appropriate.

An agent's confidence, self-assigned score, or claim of completion is not correctness evidence. Ground expected values in source material, calculations, or confirmed requirements. Distinguish a broken implementation from a mistaken local oracle; a material correction to that oracle belongs in the outer loop.

## Outer loop: review the contract

Escalate material uncertainty about meaning, scope, success criteria, conflicting evidence, or architectural commitments that determine supported behavior. Also review repeated non-improvement, exhausted budgets, and proposals that trade away a mandatory requirement. Ordinary refactoring does not require escalation.

Use [outer-review](../../../templates/outer-review.md) for a short decision packet: current contract ID, failure evidence, conflicting sources, realistic options, tradeoffs, and a recommended choice. Ask the authorized human to decide when the available instructions do not settle the issue. Continue only independent work supported by established facts and already within the authorized work unit while the dependent choice waits. Guided-mode pauses do not authorize implementation of later units. Do not treat silence, a reviewer recommendation, or an AI-generated approval as a human decision.

Record the actual decision and its source. If the contract changes, issue a new ID, update your derived checks with reasons, and rebaseline the candidate. Scores from different contracts are not directly comparable. Revalidate affected behavior and previously protected cases before resuming refinement.

## Stop and deliver

Choose finite iteration and time limits before repeated refinement. Two consecutive attempts without meaningful improvement can be an adjustable starting proposal for human review, not a universal rule. Stop improving when mandatory criteria pass and remaining work has low value, or the agreed budget requires finalization.

For a time-limited task, agree on a delivery-check buffer within the actual allocated time. Follow the task's real deadline and required later stages. Use supplied remaining time, a known deadline, or a permitted reliable clock; do not use UI automation to read the timer or claim automatic timer access or hard enforcement.

Restore the strongest candidate for the active contract, verify required files and saved state, and summarize decisions, executed evidence, and unresolved limitations. Explain what was confirmed and what remains assumed. Review key choices, evidence, and limits with the user during the permitted task-work phase; follow the guided reference for a requested [full solution review](../../../templates/solution-review.md), separate practice Q&A, comprehension, and workflow handoff. Keep delivery and human understanding ahead of another speculative iteration.
