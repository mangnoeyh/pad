# Working with this kit

This repository supports bounded problem solving with local tabular-analysis tools. Apply these instructions to work using this kit; do not impose its workflow on unrelated tasks.

- Read the actual task README, required outputs, constraints, and evaluation metric first. Task-specific instructions take precedence over this kit.
- Select the smallest useful tools. Check available packages with `python tools/check_environment.py`; do not install an entire framework for a small analysis.
- Preserve source data. Write derived files to an explicit output directory and do not silently overwrite existing work.
- For tabular inputs, inspect schema, units, nulls, duplicates, identifiers, target availability, and time/group structure before drawing conclusions. Distinguish a bounded prefix from a representative sample or a full dataset.
- Keep filters and joins auditable with input/output row counts and cardinality checks. State the denominator and units of reported values.
- For prediction, split by the real deployment boundary before fitting preprocessing. Compare with a simple baseline. Do not use target-derived or future information as features.
- Run checks that support the conclusion. Record exact commands, key results, assumptions, and unresolved limits; do not report unexecuted checks as passed.
- Use `templates/` only when helpful and adapt to required filenames and formats. Explain key decisions and evidence as work proceeds, using representative examples so the user can describe the result. Preserve actual user choices and unresolved questions in compact task-local notes; do not manufacture understanding or approval.
- Record public resources actually used with repository URL, commit or package version, file path, and purpose. See `ATTRIBUTION.md`.

## Choosing a skill

- Use `.agents/skills/double-loop-solver/SKILL.md` for multistep implementation under a stable task contract and human review of material choices. `START_HERE.md` defaults to guided collaboration: read the Skill's `references/guided-collaboration.md`, explain the problem first, wait for understanding, agree on a method/work unit, and explain progress with pauses at the agreed checkpoints. Routine commands inside an approved unit do not need repeated approval. A user-authorized autonomous mode remains available.
- Use `.agents/skills/data-triage/SKILL.md` when starting with unfamiliar tabular data or diagnosing data quality.
- Use `.agents/skills/analysis-validation/SKILL.md` when assessing an analysis conclusion, transformation, or predictive baseline before delivery.

## Controlled work environments

Follow the latest workspace rules and provided tools when access, execution, or data transfer is restricted. Do not change managed tools or settings, bypass access controls, connect an external AI or personal account, automate a UI, or transfer task material unless the environment permits that action. Public resources remain subject to the same boundaries and their licenses. Adapt and verify reused components against the actual requirements. If a later procedure restricts AI, stop drafting, editing, or coaching its answers when that procedure begins. Understanding practice belongs in the permitted work phase. These constraints apply to the controlled workspace and do not create additional restrictions for unrelated work.

## Optional bundled guidance

Use only the relevant files listed in GUIDE.md. For failures use evidence-debug; for understanding real code use code-walkthrough; for requested UI work use frontend-design; for Korean prose style use korean-report-polish. Data audit and evaluation references extend the existing data skills. No imported instruction overrides actual task constraints, human checkpoints or allowed tools.

For an existing code change or failure-path check, apply only the relevant execution-review reference. Separate saved disk files, unsaved editor content and the running application. tools/compare_notes.py optionally flags lexical changes during prose editing. tools/review_delivery.py optionally checks configured output formats and source/report freshness; hidden or ignored helper files are not automatically excluded from a real delivery.

Use tools/verify_work.py when changing source files benefit from execution traceability. Read its solver reference first: process success, test-report verification and task completion are distinct claims. Store records only in the actual task workspace; tools/run_unit_tests.py can generate a standard test report without additional packages.
