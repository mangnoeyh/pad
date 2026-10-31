#!/usr/bin/env python3
"""Report local runtime/package availability without installation or network requests."""
from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import sys

PACKAGES = {
    "pandas": "pandas", "numpy": "numpy", "duckdb": "duckdb",
    "openpyxl": "openpyxl", "pyarrow": "pyarrow", "scikit-learn": "sklearn",
    "matplotlib": "matplotlib", "pandera": "pandera",
}


def check_environment() -> dict:
    packages = {}
    for distribution, module in PACKAGES.items():
        try:
            installed = importlib.util.find_spec(module) is not None
        except (ValueError, ModuleNotFoundError):
            installed = False
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            version = None
        packages[distribution] = {"available": installed, "version": version}
    return {
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "working_directory": str(Path.cwd()),
        "working_directory_writable": os.access(Path.cwd(), os.W_OK),
        "commands": {name: shutil.which(name) for name in ("git", "uv", "pip")},
        "packages": packages, "core_available": packages["pandas"]["available"],
        "note": "Inventory only: optional packages are not required for every task. Availability does not guarantee a successful import. No installation or network request was performed.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print a JSON inventory.")
    args = parser.parse_args(argv)
    report = check_environment()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Python {report['python']['version']}: {report['python']['executable']}")
        print(f"Platform: {report['platform']['system']} / {report['platform']['machine']}")
        print(f"Working directory writable: {report['working_directory_writable']}")
        for name, info in report["packages"].items():
            print(f"{name}: {info['version'] or 'version unknown'}" if info["available"] else f"{name}: not installed (optional unless needed)")
        print(report["note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
