"""Read two local UTF-8 notes and report changed lexical candidates."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import stat
import sys

MAX_BYTES = 256 * 1024
MAX_FINDINGS = 50
MAX_VALUE_CHARS = 512
NOTE = "No findings is not semantic proof; candidates require human interpretation."
SCOPE = "lexical-candidates"
NUMBER = r"[+-]?(?:(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?"
UNITS = (
    "킬로그램", "킬로미터", "밀리미터", "센티미터", "미터", "리터",
    "퍼센트", "백만원", "천만원", "억원", "만원", "조원", "시간",
    "kg", "mg", "km", "cm", "mm", "mL", "ml", "kW", "MW", "kWh",
    "GHz", "MHz", "kHz", "Hz", "TB", "GB", "MB", "KB", "ms", "min",
    "°C", "℃", "°F", "%", "g", "m", "L", "s", "h", "W", "V", "A", "K",
    "원", "명", "개", "건", "회", "배", "일", "주", "월", "년", "분", "초",
    "톤", "도", "평",
)
UNIT_PATTERN = "|".join(re.escape(x) for x in sorted(UNITS, key=len, reverse=True))
QUANTITY = re.compile(
    r"(?<![A-Za-z0-9_.])(?P<prefix><=|>=|<|>|≤|≥)?[ \t]*"
    r"(?P<number>" + NUMBER + r")"
    r"(?:[ \t]*(?P<unit>" + UNIT_PATTERN + r")(?![A-Za-z]))?"
    r"(?:[ \t]*(?P<suffix>이상|이하|초과|미만))?"
)
QUOTES = re.compile(
    r'''"([^"\r\n]+)"|(?<!\w)'([^'\r\n]+)'(?!\w)|“([^“”\r\n]+)”|‘([^‘’\r\n]+)’|「([^「」\r\n]+)」|『([^『』\r\n]+)』'''
)


def validate_arguments(project, before, after):
    """Reject network-like spellings before any filesystem operation."""
    for value in (project, before, after):
        if not isinstance(value, str) or not value or "\x00" in value:
            raise ValueError("Paths must be nonempty strings without NUL characters.")
    candidate = project.strip()
    if (len(candidate) >= 2 and all(c in "/\\" for c in candidate[:2])):
        raise ValueError("The project must be a local directory.")
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", candidate) and not re.match(r"^[A-Za-z]:[\\/]", candidate):
        raise ValueError("URL project paths are not supported.")
    for value in (before, after):
        if (value.startswith("/") or "\\" in value or ":" in value
                or ".." in value.split("/")):
            raise ValueError("Note paths must be relative, use '/', and contain no '..'.")


def read_note(root, relative):
    target = (root / relative).resolve(strict=True)
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError("A note path resolves outside the project.") from None
    if not stat.S_ISREG(target.stat().st_mode):
        raise ValueError("Each note must be a regular file.")
    with target.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("A note exceeds the 256 KiB limit.")
    return raw.decode("utf-8-sig", errors="strict")


def atoms(text):
    found = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for match in QUANTITY.finditer(line):
            value = "".join(match.group(name) or "" for name in ("prefix", "number", "unit", "suffix"))
            found.append({"kind": "quantity", "value": value, "line": line_number})
        for match in QUOTES.finditer(line):
            content = next(group for group in match.groups() if group is not None)
            found.append({"kind": "quote", "value": " ".join(content.split()), "line": line_number})
    return found


def envelope(before, after):
    return {"schema": "note-comparison-v1", "status": "error", "scope": SCOPE,
            "before": before, "after": after, "counts": {}, "findings": [],
            "limits": {"max_file_bytes": MAX_BYTES, "max_findings": MAX_FINDINGS,
                       "max_value_chars": MAX_VALUE_CHARS},
            "findings_total": 0, "findings_reported": 0, "findings_truncated": 0,
            "note": NOTE}


def compare(project, before, after):
    validate_arguments(project, before, after)
    root = Path(project).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("The project must be an existing directory.")
    left, right = atoms(read_note(root, before)), atoms(read_note(root, after))
    key = lambda item: (item["kind"], item["value"])
    left_count, right_count = Counter(map(key, left)), Counter(map(key, right))
    removed, added = left_count - right_count, right_count - left_count
    total_removed, total_added = sum(removed.values()), sum(added.values())
    findings = []
    for change, items, remaining in (("removed", left, removed), ("added", right, added)):
        for item in items:
            item_key = key(item)
            if remaining[item_key]:
                remaining[item_key] -= 1
                if len(findings) < MAX_FINDINGS:
                    finding = {"change": change, **item}
                    if len(item["value"]) > MAX_VALUE_CHARS:
                        finding.update(value=item["value"][:MAX_VALUE_CHARS],
                                       value_truncated=True, value_length=len(item["value"]))
                    findings.append(finding)
    total = total_removed + total_added
    result = envelope(before, after)
    result.update(status="review" if total else "no_findings", findings=findings,
                  counts={"before": len(left), "after": len(right),
                          "removed": total_removed, "added": total_added},
                  findings_total=total, findings_reported=len(findings),
                  findings_truncated=total - len(findings))
    return result


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main(argv=None):
    result = envelope(None, None)
    parser = JsonArgumentParser(description="Compare lexical candidates in two local UTF-8 notes.")
    for name in ("project", "before", "after"):
        parser.add_argument("--" + name, required=True)
    try:
        args = parser.parse_args(argv)
        result = envelope(args.before, args.after)
        result = compare(args.project, args.before, args.after)
        code = 1 if result["status"] == "review" else 0
    except (OSError, UnicodeError, ValueError, RuntimeError) as error:
        result["error"] = str(error)
        code = 2
    print(json.dumps(result, ensure_ascii=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
