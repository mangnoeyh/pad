# Validation

Verified locally on 2026-10-30. This is execution evidence for this toolkit, not certification of a deployment or managed workspace.

## Environment

- Windows x86-64, CPython 3.12.14
- pandas 3.1.0, numpy 2.5.4
- DuckDB 2.0.0
- scikit-learn 1.9.1
- openpyxl 3.1.5, pyarrow 26.0.0

The requirements files allow compatible version ranges; these are the exact versions used for this validation. Availability in another environment must be checked there.

## Automated checks

```bash
python -m unittest discover -s tests -v
```

Result: **37 tests passed, no skipped tests**.

The suite checks bounded input scope, exact versus unknown row counts, missing values, duplicates, malformed files and headers, Excel/Parquet readers, input/output protection, SELECT-only local SQL, disabled external SQL access, result limits, trailing comments and quoted semicolons, reproducible synthetic data, time/group split boundaries, train-only preprocessing, unseen categories, classification/regression outputs, and URL/network-share rejection.

All three bundled Skills passed the skill-creator frontmatter validator after the double-loop addition. That structural check does not prove a Skill makes correct decisions on every task.

## End-to-end run

A 200-row fully synthetic CSV completed the documented environment check, inspection, grouped SQL query, and time-split classification path. The profile reported an exact 200 rows; time boundaries were strictly ordered; timestamp, equipment, and target were excluded from predictor columns. The run produced profile JSON/Markdown, grouped CSV, and model metrics/predictions/report outside the source tree.

## Limits

- Other deployment and managed workspaces have not been exercised by this local validation.
- Default inspection/query input scope is a bounded prefix, not a random sample.
- The predictive example uses one holdout; random splitting is not stratified.
- Task-specific feature availability, causal interpretation, representativeness, and metric suitability still require judgment.

## Double-loop preparation rehearsal

The original double-loop guidance and startup/templates were exercised by an independent agent on one small synthetic ticket-summary task in an isolated local workspace.

- The first stage exposed an unresolved denominator policy, reported both labelled alternatives, and requested a concrete user decision rather than presenting an assumed policy as confirmed.
- After the user specified latest-ticket status and exclusion of cancelled tickets, the agent recorded a new contract ID and regenerated the report under that contract.
- The final result contained two teams with completion rates 0.5000 and 1.0000. Seven calculation/source-preservation checks and final snapshot-integrity verification passed. The previous contract's snapshot remained available.
- Source README/data were preserved; an independent final CSV check confirmed columns, counts, and four-decimal formatting.

This is one exercised workflow scenario, not a benchmark of task success or a programmatic guarantee of approval, iteration, or deadline enforcement. No Python tool implementation changed in this documentation/Skill update.

## Guided collaboration rehearsal — 2026-10-31

A fresh agent exercised the revised candidate guidance on one separate, synthetic five-row order-history task. The test driver supplied controlled simulated user turns; these are interaction tests, not actual user understanding or performance in other workspaces.

- The agent explained the problem and stopped before solution design or implementation. When the simulated user expressed confusion, it gave a smaller example and again waited. The task folder still contained only the original README and input CSV at this point.
- After an explicit understanding confirmation and business-rule answer, it proposed a method and a bounded input-check unit, recorded the actual supplied decisions, and waited for authorization of that unit.
- With authorization for input inspection only, it executed checks, reported five rows/four orders, traced one order from history to the representative record, distinguished unverified execution details, and paused before the next implementation unit. No final program or aggregate CSV was generated. The original README and data hashes were unchanged.
- A controlled transition to an AI-prohibited follow-up phase stopped answer assistance rather than producing the requested response.
- All three Skills passed frontmatter validation; twelve local documentation links resolved. An independent semantic review found no material conflict between guided checkpoints, authorized routine commands, and the boundary of an AI-restricted procedure.

This rehearsal covers one interaction scenario and a real input-check unit. It does not establish full-solution correctness, performance on unseen tasks, a user's comprehension, or automatic enforcement of pauses, permission, or time limits. Python tools were unchanged, so the earlier 37-test execution remains historical evidence rather than a newly rerun suite.

## Double-loop explanation and practice Q&A — 2026-10-31

The Korean application guide and startup now explain bounded automatic improvement within an agreed unit and practice Q&A before submission confirmation, during the AI-permitted work phase. A fresh agent performed a read-only Q&A rehearsal using the completed input-inspection unit from the synthetic order-history fixture.

- It produced six practice questions with short example answers, file/line evidence and possible follow-up questions. It separated the simulated user's decisions from the agent's execution and the completed unit from unfinished implementation.
- It explicitly identified the absence of a final program, aggregate CSV and full command verification, rather than inventing completion or human-performed checks. Protected source hashes remained unchanged.
- The updated Skill passed frontmatter validation, thirteen local document links resolved, and an independent semantic review found no material conflict between bounded improvement, user checkpoints, or the AI-prohibited follow-up boundary.

This verifies one grounded Q&A scenario and documentation consistency. It does not predict real questions, establish full-solution accuracy, or prove the user's understanding. The earlier end-to-end and guided interaction evidence retain their stated scope; Python implementations were unchanged.


## Earlier utility revision — 2026-10-31 (replaced)

The following results describe the previous implementation. It has since been removed and replaced by the original tools described below.

- Integrated suite: 64 tests discovered, 63 passed, 1 skipped on Windows because creating a symbolic link requires an unavailable privilege. The ordinary empty-file, malformed-JSON and path-escape checks still ran.
- The added checks exercise real success/failure/timeout, empty or skipped tests, command/output/source mismatches, stale evidence, missing plan entries, and the public CLI. NaN and Infinity timeouts are rejected before a child process starts.
- The original module was tested locally, then imported with the finite-timeout correction. Its path test was split to isolate the platform-dependent symlink check. These adaptations are recorded in vendor/manifest.json.
- Seven Skill entrypoints passed structural validation; 51 local Markdown links and 20 imported file hashes matched. Independent review checked tool-result scope, license retention and the existing guided collaboration boundaries.
- Validation used the available Python runtime and isolated local package directory. A writable workspace temporary directory was selected for this Windows sandbox. No managed tool update, external model connection or project installation script was executed.
- These are local synthetic checks. They do not establish correctness for a future task, compatibility with every runtime, actual user understanding, or delivery through another platform.

## Original verification tools — 2026-10-31

- The previous imported execution module, schema, templates and adapted tests were removed from the current tree together with their import records and license notice. Other imported guidance retains its notices.
- tools/verify_work.py and tools/run_unit_tests.py use an original record format and newly authored tests. Initial implementation and independent test drafts were produced in separate contexts that received behavioral requirements without the removed source or tests. Integration review added path guards, timeout cleanup and focused regressions.
- Combined suite: 73 tests discovered, 72 passed, 1 skipped because Windows could not create a directory symbolic link. Ordinary output-path escape checks ran successfully.
- After making the cleanup regression portable, all 18 focused verification tests passed without skips.
- An additional seven-check CLI flow covered real unittest XML generation, verification, invalidation after source changes, a fresh rerun, and rejection of a failing regression.
- Coverage includes empty/skipped/failed/error or inconsistent XML, malformed records, changed source/log/report/metadata, existing-report protection, finite timeouts, missing paths, no-shell arguments, project imports and preserved separate records.
- Mixed-separator network paths are rejected before filesystem access. Bounded wait intervals avoid operating-system conversion overflow for very large finite timeouts. Wait errors terminate and reap the started child.
- Successful process execution is distinct from verified test evidence. Both the original report and its archived snapshot are checked. Verification does not establish the completeness or correctness of acceptance criteria, user understanding, or actual delivery.
- No new framework, model connection, managed configuration or tool update is required.

## Note and delivery review utilities — 2026-10-31

- Added independently authored, standard-library tools for lexical note comparison and local delivery review. Implementation contexts received behavioral specifications without external implementation or tests; integration review added focused boundary checks.
- Current combined suite: **111 tests discovered, 109 passed, 2 skipped**. The skips are Windows directory symbolic-link cases that require an unavailable privilege. Ordinary malformed-input, path and preservation checks ran.
- A separate eight-check CLI flow exercised fact-preserving reorder, a changed comparison boundary, current delivery capture/check, source-change invalidation, a new receipt, hidden extra-file detection and a clean recheck.
- Note comparison checks bounded numerical/unit/comparison and quotation candidates as multisets. Repeated unclosed quotation marks are covered. Its no-findings result is not proof that meaning, negation, subjects or references were preserved.
- Delivery checks cover required output presence, text/strict JSON/CSV structure, configured file hashes, stale receipts, hidden extra files, bounded local paths and decoder-error classification. A receipt records unsigned local consistency, not correctness, test success, editor state or platform receipt.
- All seven Skill entrypoints passed structural validation. All 58 local Markdown links resolved and the 13 retained import hashes matched. Independent review found no material conflict with the guided understanding and agreed-unit boundaries.
- Tools remain optional and conditional on actual task requirements; no new framework, installation, model connection or managed tool update is required. These checks use local synthetic fixtures and do not establish future-task success.

## Conditional application checks — 2026-10-31

- Added original guidance for checking actual API response status, content type, body and state transitions, limited static ID references and human preview checks. Added conditional requirement-based properties with a known-answer case and an explicit supported domain.
- No executable implementation, dependencies, managed configuration or existing license notices changed. The prior 111-test result retains its stated execution scope; it was not rerun for this documentation-only change.
- All seven Skill entrypoints passed structural validation; 61 local Markdown links resolved and 13 retained import hashes matched. The local synthetic curl illustration could not connect to its loopback server (exit 7), so no live HTTP or rendered-UI success is claimed for this revision. The curl behavior is documented from the official manual and must be checked against the actual permitted application.

## Shared-work review guidance — 2026-10-31

- Added conditional guidance for independent work with explicit file ownership, read-only review, shared-state coordination, isolated fixtures and integration verification. Existing user checkpoints remain in force; no new sessions, configuration changes or orchestration dependency are required.
- Added limited checks for stale asynchronous UI responses and duplicate state-changing requests when those behaviors are relevant. Automation-effect estimates, only when requested, distinguish measurements and assumptions, one-time work and recurring human review or exception handling.
- All seven Skill entrypoints passed structural validation. The 61 local Markdown links and 13 retained import hashes remain valid. No executable implementation or dependency changed; the earlier 111-test result remains historical execution evidence, with no new end-to-end UI, concurrency or ROI-success claim.

## Startup revision selection — 2026-10-31

- Startup now compares an existing kit copy with the public default-branch commit, reuses only a clean current copy and preserves older or modified copies while obtaining a separate fresh copy when possible. A failed download is reported without repeated retries. Actual task instructions and source data remain protected.
- Explicitly states that relevant Skills and verification tools may be selected within the agreed unit without the user naming them, with concise purpose, observation and limitation updates. Existing understanding and decision checkpoints remain unchanged.
- Local startup text exports match the first text block. All 61 local Markdown links and 13 retained import hashes remain valid; executable implementations and dependencies are unchanged. This documentation check does not establish Git network access or startup behavior in another workspace.

## Web state and data-flow guidance — 2026-10-31

- Added conditional web-state checks for input validation, concurrent/duplicate requests, changing inputs, completion-order reversal, network/storage failure, retries, reload, cancellation and actual role boundaries. Policies remain requirement-driven; no queue, framework, missing feature or deployment guarantee is imposed.
- Data-ingestion checkpoints and the solution-review/practice templates now trace actual input paths, reader functions, parsed types, validation, matching/filtering, computation and storage/output. Unknown implementation details remain unknown.
- An independent read-only review found no blocking routing/scope conflict. In one synthetic trace exercise, it distinguished a correct visible result from a stale server current-result pointer, and treated retry/deduplication and preservation claims without observations as unverified. A retry-identity clarification was incorporated. This is guidance evaluation, not an executed application/concurrency test.
- All 63 local Markdown links and 13 retained import hashes matched; startup text exports remain synchronized. All seven Skill entrypoints are byte-identical to the preceding validated revision. The frontmatter validator could not run in the current sandbox because its previous PyYAML directory was inaccessible; no new structural-validator pass is claimed.
- Executable implementations and dependencies are unchanged, so the prior 111-test execution retains its stated historical scope. No application source was supplied for this review, and no live UI, concurrent request, storage-recovery or input-pipeline success is claimed.

## Adaptive parallel routing — 2026-10-31

- Added bounded role/model guidance: primary dialogue and integration, independent implementation workers, light read-only classification and review. Default preferences use available 6.1 Sol medium for implementation and available 6.0 Luna for light work; other models require actual menu/tool support. Missing per-worker settings fall back to same-model parallel work or sequential execution.
- Main-session setting changes remain the user's action. Human understanding and decision pauses, single-writer ownership, short task context, actual diff checks and integration verification are preserved. No configuration, provider, model connection, CLI update or launcher was installed.
- During authoring, a focused draft agent was requested with Sol medium and a bounded read-only review agent with Luna low. The review found no material checkpoint/model-policy conflict. This does not benchmark latency, prove target-workspace model availability or establish the cause of any earlier slowdown.
- Read-only local CLI help and official subagent documentation were inspected for capability boundaries. Exact behavior in a different or managed client remains unverified. Model/tool/computation waits should be distinguished from unsupported congestion assumptions.
- All 66 local Markdown links and 13 retained import hashes matched. All seven Skill frontmatter blocks are unchanged and startup text exports are synchronized. Executable implementations and dependencies are unchanged; no new application test run or performance result is claimed.

## Bounded worker task decomposition — 2026-10-31

- Expanded parallel-work guidance with one-outcome task packets, explicit inputs/interfaces/file ownership, dependencies, acceptance evidence and assigned remaining repair budget. Internal dispatch stays within the agreed human work unit and its checkpoints; workers do not recursively create unlimited work.
- Same-file edits are serialized with an ownership handoff. A frozen interface can support independent API/UI/test preparation in parallel; actual integration/execution waits for required implementations and environment. Splitting work does not reset the shared budget or justify extra architecture.
- An independent read-only review identified the missing packet/dependency/budget details. A synthetic planning exercise initially serialized interface-ready work; the distinction was clarified and the follow-up plan separated parallel preparation from dependent runtime integration, preserved the total repair budget and excluded an unauthorized feature. This is guidance evaluation, not application implementation or a speed benchmark.
- All seven Skill frontmatter blocks are unchanged. Startup text exports match the first text block, all 66 local Markdown links resolve and 13 retained import hashes match. Public identifier checks remain clear. No executable implementation or dependency changed; no new application test or performance result is claimed.

## Optimization and verification checks — 2026-10-31

- Added original, conditional guidance for fixed-input optimization: baseline timing, feasibility versus objective, reduced screening versus full-input validation, same-version incumbents, valid perturbations and uncertainty about optimality. Predictive holdout protections remain separate.
- Added an optional isolated known-defect check, a precise overall-rate versus group-average distinction and conditional keyboard/focus/narrow-screen/long-value UI checks. No external implementation, installer or framework was imported; retained notices are unchanged.
- In a private, standard-library synthetic fixture, the normal baseline passed, a deliberate boundary defect failed the intended assertion, and the restored original passed with the same bytes. This exercises that procedure only, not any application or overall test-suite quality.
- An independent read-only guidance exercise rejected full-input adoption without validation, reuse of an old-input incumbent, relabelled predictive holdout tuning and an unrelated import failure as defect-detection evidence. A review-scope note limits final Q&A preparation to the completed-work phase.
- All seven Skill frontmatter blocks are unchanged, 69 local Markdown links resolve and 13 retained import hashes match. Startup text exports remain synchronized and current identifier scans remain clear. Executable implementations and dependencies are unchanged; the earlier 111-test run remains historical evidence, with no new full-suite, UI-accessibility or application-optimization success claim.

## Baseline-to-delivery workflow — 2026-10-31

- Connected condition roles/scope/status, low-cost feasibility checks, whole-change cost estimates, rebuildable baseline preservation and candidate promotion to the existing workflow and templates. Existing human checkpoints and authoritative requirements remain binding; routine approved commands do not gain extra approval gates.
- Final verification now links the delivery source/build/run/input/configuration/result/output, using only actual required components and isolated startup checks. Earlier running processes or unchanged data hashes are not evidence that a newer delivery source reproduces the result.
- A private report-only workflow review separated recorded historical claims from unavailable code/runtime evidence. An independent synthetic guidance review distinguished old versus new contracts, reduced/relaxed experiments and differing source/runtime candidates. A separate synthetic capacity-bound calculation confirmed a necessary-condition failure without assuming a group must use only one batch. No actual application or solver was tested.
- All seven Skill frontmatter blocks are unchanged. The startup exports are synchronized, 73 local Markdown links resolve and 13 retained import hashes match. The original private report bytes remain unchanged, and identifiers from that report are excluded from current public files.
- Executable implementations and dependencies are unchanged; prior full-suite execution retains its historical scope. This revision makes no claim about a historical service, live runtime, actual delivery receipt or future task outcome.
