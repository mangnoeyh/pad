---
name: data-triage
description: Inspect unfamiliar local tabular data, identify quality and leakage risks, and choose a minimal analysis plan before implementing an analysis or predictive baseline.
---

# Data triage

Use this skill to decide what can be learned from the available data. Do not invent a business target, a required deliverable, or a modeling requirement.

1. Read the task README and data descriptions. Extract the decision to support, required outputs, metric, constraints, and unanswered questions. If the task provides a domain or role agent, ask only about information that changes a decision; do not contact external people or services without authorization.
2. Locate input files and check available packages. From the kit root, use `python tools/check_environment.py` and `python tools/inspect_data.py INPUT --output-dir OUTPUT_DIR` when suitable. Use `--help` for format, encoding, sheet, and row-limit options.
3. Inspect column meanings, units, types, nulls, duplicates, plausible ranges, identifiers, target balance, and time/group boundaries. Check examples against documentation; do not silently coerce a field merely to make code run.
4. Establish the inspected scope. The bundled inspection tool reads a bounded prefix by default, not a random sample. Read its sample/count metadata. Flag missing populations and order bias; do not turn unknown total rows into a claimed count.
5. For multiple tables, establish keys and expected cardinality before joining. Check unmatched keys and before/after row counts. For prediction, identify when each feature becomes available and exclude information unavailable at prediction time.
6. Propose the smallest useful next step, a simple comparison or baseline, and the validation that could falsify it. Prefer a direct aggregate when a model adds no value.

Produce a short summary of observed facts, assumptions, important risks, and the next action. Use `templates/plan.md` only if a written plan helps or is requested. Preserve raw data and keep outputs local to the task workspace.

When this task needs predictive data checks, read [additional checks](references/data-audit.md). The task instructions and actual deployment scenario remain authoritative.
