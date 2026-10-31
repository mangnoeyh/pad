Run `python tools/compare_notes.py --project DIR --before relative.txt --after relative.txt`.
Standard output is one JSON object. Exit codes are 0 for `no_findings`, 1 for
`review`, and 2 for `error`. `--help` prints conventional help and exits 0.
Inputs are read only; no files are created or changed.

The project must be an existing local directory. Note paths use forward slashes,
remain relative, contain no parent traversal, colon, or backslash, and resolve to
regular files inside the project. Network and URL spellings are rejected before
filesystem access. Each read is bounded to 256 KiB plus one overflow byte. UTF-8
is strict, with an optional initial BOM.

The original lexical algorithm compares multisets of numeric candidates and
single-line direct quotes. Quantities retain adjacent operators, common units,
and Korean comparison suffixes. Number spelling remains significant. Reordering
is allowed; duplicate additions and removals remain visible. Quote delimiters and
whitespace normalize, but quoted content otherwise remains literal. Unclosed or
multiline quotes are not recognized. Negation, paraphrases, context, and semantic
equivalence are outside the algorithm's scope.

JSON includes `schema`, `status`, relative `before` and `after`, `scope`, counts,
and findings with `change`, `kind`, `value`, and a one-based `line`. At most 50
findings are reported, with total, reported, and truncated counts. Individual
values over 512 characters are shortened and marked with `value_truncated` and
`value_length`; full candidate values still participate in comparison. Candidate
values can include quoted excerpts, but raw whole-note fields are never included.
`no_findings` is not semantic proof. An error includes a diagnostic `error` string.

Validation: `python -m unittest discover -s tests -v`.
