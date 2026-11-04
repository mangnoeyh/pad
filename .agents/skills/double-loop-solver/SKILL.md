---
name: double-loop-solver
description: Solve multistep tasks with evidence-based iterations and human review of important choices. Coordinate autonomous implementation workers with user-led operational discovery and optimization, including iterative stakeholder clarification; skip for simple edits.
---

# Double-loop solver

Deliver the requested result under an explicit task contract. The inner loop improves a candidate under that contract; the outer loop resolves evidence that the contract needs correction. This workflow is not a correctness guarantee.

## Scope and reading order

Use the actual request to select the collaboration mode and deliverables. The default launch request selects a comprehension pause, main/user discussion with autonomous E2E workers, early learning, user-ended improvement rounds, a full explanation and separate practice Q&A. Directly invoking this skill does not by itself authorize all of those outputs or pauses. Honor an explicitly different mode and existing authorization; silence is not consent.

Read relevant detail at its trigger, then reuse it. Do not read the launch prompt again, preload this whole reference library, or execute examples as startup checks. References are relative to this skill; templates and tools belong to the kit, while real inputs, outputs and notes belong to the task workspace.

| Trigger | Read / act |
| --- | --- |
| Initial understanding or explaining a material choice | [Guided collaboration](references/guided-collaboration.md). Identify the required artifact and what makes it useful; mixed tasks can need different checks for different parts. In the selected default mode, explain the problem and await understanding before design or implementation. |
| Checking or using workers | [Parallel work](references/parallel-work.md). Verify actual execution and waiting-state behavior; use small independent tasks with explicit ownership. Main owns integration and confirmed decision handoff. |
| Understanding confirmed | Briefly explain the simplest valid E2E approach and start the already-authorized independent work without routine reapproval. Main begins operational discovery through [stakeholder questions](references/stakeholder-questions.md). |
| A method choice materially affects quality, time or resources | Proactively compare suitable methods through [method selection](references/method-selection.md) and only relevant parts of the [method index](../../../docs/methods/INDEX.md). Explain the tradeoff plainly; ask the unresolved business decision, not an algorithm-name quiz. |
| A configurable service, rule change, partial candidate or candidate adoption | Read the relevant sections of [baseline and delivery](references/baseline-and-delivery.md) for authority, dynamic policies, recovery, feasibility and current-version validation. |
| First actual input-to-output path with relevant essential checks | Provide the selected learning draft immediately through guided collaboration. If operational judgment matters, dispatch the independent operational omission review in parallel work alongside learning and optimization; it is distinct from functional testing. |
| First optional improvement, a round checkpoint or resuming prior work | [Improvement rounds](references/improvement-rounds.md) owns the round state, real continue/end reply, one current-state note and cumulative history. Passing tests or a claimed optimum is not default permission to end. |
| Meaningful results, a partial stakeholder answer or new operational anomaly | Revisit stakeholder questions. Measure the relevant unexamined perspective, narrow the unanswered fact, or propose the consequential user choice. Do not invent hidden rules. |
| Authorized improvement end or actual deadline/access limit | Complete required repairs, integration and relevant delivery checks, then reconcile requested explanation/Q&A with the final candidate. Use baseline and delivery plus guided collaboration. Report the true stop reason. |

Only independent authorized work continues while a decision waits. Respect a whole-work pause. A running worker, actual human reply, tested result and submission are separate observable events; do not infer one from another.

## Contract and evidence

Use the necessary fields of [task-contract](../../../templates/task-contract.md) in existing notes; do not create paperwork merely to fill templates. Record the contract ID, required output, source-backed constraints, acceptance checks, unresolved assumptions, permitted tools and actual remaining budget. Keep rule source separate from enforcement: a user-added hard policy is still user-revisable; task mandates remain protected. Configurable services need reusable policies for current inputs/settings, not developer approval of each runtime result.

Preserve authoritative instructions, raw supplied data and official expectations. Edit starter files when required, keep derived material separate, and follow explicit source precedence. Do not silently weaken a check or discard a failing case. Keep conflicting evidence and seek only the clarification that the available authority cannot resolve.

Use only permitted tools and actually available models. This skill does not authorize upgrades, external AI, new accounts or UI automation. Share the real time/resource budget across workers and rounds, including delivery and learning time; do not invent elapsed times, deadlines or timer access.

## Inner and outer loops

For a bounded iteration, capture the failure or opportunity and observed evidence, state a hypothesis, make the smallest useful change and run relevant checks. Compare against the saved incumbent under the same contract and input/settings. Preserve a reproducible valid candidate; mandatory gates and protected conditions precede score. [Cycle-log](../../../templates/cycle-log.md) supplies optional evidence fields, not another workflow.

Confidence, self-scores and completion messages are not correctness evidence. Ground expected results in sources, calculations or confirmed criteria. Distinguish implementation failure from an incorrect local oracle. Partial or worse candidates can justify bounded repair; baseline and delivery defines when user-policy changes or exceptions may restore them without relaxing task mandates.

Review material uncertainty in meaning, scope, success criteria, conflicting sources or a proposed contract change in the outer loop. Prepare a short evidence/options/recommendation packet using [outer-review](../../../templates/outer-review.md) if useful. Apply established decisions and delegated ranges directly; otherwise wait for the authorized person's real decision while unrelated implementation continues. Reviewers cannot grant that authority.

Record the actual decision and source. If it changes the contract, assign a new version, explain changed checks, notify affected workers and revalidate candidates before adoption. Compare algorithms under the same criteria; explain policy changes separately. Bounded round execution, continued improvement and finalization follow the single lifecycle in improvement rounds.

## Verification by affected surface

Read only applicable guidance when planning that work. Pass relevant failure conditions directly to workers.

| Surface | Reference |
| --- | --- |
| Failure diagnosis or minimal repair | [evidence-debug](../evidence-debug/SKILL.md) |
| Existing code, negative paths, editor/disk/server discrepancies or integration | [execution review](references/execution-review.md) |
| Web UI / HTTP API | [app checks](references/app-checks.md); stateful input, identity, recomputation or saved commands additionally use [web state checks](references/web-state-checks.md) |
| Tabular analysis, transformations, prediction or ranking evaluation | [data triage](../data-triage/SKILL.md) for unfamiliar tabular inputs, then relevant [analysis validation](../analysis-validation/SKILL.md); do not add a predictive model when the task does not need one |
| Fixed-input optimization | [optimization validation](../analysis-validation/references/optimization-validation.md): feasibility, proxy screening and full-input evidence are distinct |
| Source-backed analysis, policy decisions, explanations or learning content | [content checks](references/content-checks.md); use alongside data or app checks when those surfaces are also present |
| Repeated checks against changing source | [evidence tools](references/evidence-tools.md), only if the bundled runner adds useful traceability |
| Final running and delivered candidate | baseline and delivery; [delivery review](references/delivery-review.md) if using its optional file-check tool |

Verify integrated artifacts, not just worker reports. A technical countercheck at a material implementation boundary does not replace the first-E2E operational review. Resolve material review findings through an actual check, factual question or evidence-backed deferral before recommending the end, while respecting a real end instruction and task limits. Record who discovered each issue, what was fixed and what was actually rechecked. A zero-test run, all skips, a sample-only success, HTTP checks and human UI observations support different claims.

Use the strongest verified candidate for the active contract. Follow the selected learning mode for the [solution review](../../../templates/solution-review.md) and separate practice Q&A. Keep assumptions and unverified limits visible; actual delivery and the user's understanding matter more than another speculative iteration.
