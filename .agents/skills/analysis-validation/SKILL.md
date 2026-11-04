---
name: analysis-validation
description: Validate a local tabular analysis, transformation, or predictive baseline using scope checks, independent calculations, leakage checks, and reproducible evidence before reporting results.
---

# Analysis validation

Choose checks that could change the conclusion. Avoid adding a large test suite for a one-off reversible analysis.

## Aggregates and transformations

- Confirm input files, filters, row scope, units, time zones, and the denominator. A prefix-based result supports claims about that prefix until full coverage is established.
- Reconcile row counts before and after filtering, joins, deduplication, and missing-value handling. Check join cardinality and unmatched keys.
- Recompute a key number through a different route when practical: a small hand-check, a grouped subtotal, or a local SQL query. From the kit root, `tools/query_data.py INPUT --sql "SELECT ... FROM data" --output OUTPUT.csv` can help; its input/output row limits still apply.
- Check boundaries that matter to the task: empty groups, zero denominators, missing categories, extreme values, and dates around a cutoff.

For an overall rate, confirm whether the contract means summed numerators divided by summed denominators or an average of group rates. They are different metrics: groups 1/2 and 9/10 yield an overall 10/12, while the unweighted average group rate is 70%. Do not silently exchange them.

## Fixed-input optimization, when relevant

When comparing solutions for supplied fixed inputs, read [optimization validation](references/optimization-validation.md). Separate full-input feasibility/objective checks from reduced screening and from predictive holdout evaluation. Preserve a valid incumbent for the same input version and confirmed contract; a timeout is not an infeasibility or optimality proof.

## Requirement-based properties, when useful

Choose a small property that follows from the confirmed contract, with a supported input domain, an explicit transformation and an expected relation. For example, an order-independent aggregate should keep the same keyed values after input shuffling; a normalization specified as idempotent should satisfy `clean(clean(x)) == clean(x)`; serialization should round-trip only the types and precision it promises to support. These examples are conditional, not universal requirements: order invariance does not apply to time-ordered operations.

Use existing tests or a few fixed cases and a bounded seeded generator from the standard library. Keep a separate known-answer example; consistency alone can hold for an incorrect function. Retain a small failing input as a regression case. No new property-testing dependency is required. This application draws on [Hypothesis's property and state testing concepts](https://hypothesis.readthedocs.io/en/latest/stateful.html), without importing its code or claiming its coverage.

## Predictive baselines, when relevant

- Match the split to deployment: time, entity/group, or independent rows. Check overlap explicitly. Fit imputers, encoders, scaling, and feature selection on training data only.
- Exclude target-derived fields, post-outcome information, and identifiers that leak the split. Compare with a simple baseline using the same holdout and appropriate metric.
- Check class coverage or target ranges, subgroup errors, and instability when these affect the decision. Do not tune repeatedly against the final holdout and then describe it as untouched.
- Treat `examples/tabular_ml.py` as an editable example, not proof that random splitting or its model fits the task.

## Ranking evaluation, when relevant

For ranking recommendations, choose a baseline and metric that match the actual users, candidate items, time boundary and available relevance or feedback. Classification/regression example performance is not ranking quality. Check whether feedback exists only for exposed items and what can be assessed for new users/items. Offline evaluation does not establish live usage, revenue or satisfaction gains; do not add an unrequested experiment system or collect new data just to claim those gains.

## Delivery evidence

Rerun the essential path from the recorded command when feasible. Check required filenames, schemas, saved state, and outputs against the task README. State what actually ran, its result, what remains unverified, and the consequence of the main limitation. Use `templates/report.md` and `templates/decisions.md` when helpful; do not claim checks passed without execution evidence.

When this task needs predictive or ranking evaluation, read [additional checks](references/honest-eval.md). The task instructions and actual deployment scenario remain authoritative.
