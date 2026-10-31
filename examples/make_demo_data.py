"""Generate a small, fully synthetic CSV without downloading any data."""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import random


def local_path(value: str | Path) -> Path:
    """Reject URL and network-share paths before resolving or touching them."""
    def reject_network(raw: str) -> None:
        if raw.startswith(("//", "\\\\")) or "://" in raw or re.match(r"^[A-Za-z][A-Za-z0-9+.-]{1,}:", raw):
            raise ValueError("Only local filesystem paths are supported; URLs and network shares are rejected")
    reject_network(str(value))
    resolved = Path(value).resolve()
    reject_network(str(resolved))
    return resolved


def make_demo_data(output_dir: Path, rows: int = 200, seed: int = 42) -> Path:
    if rows < 20:
        raise ValueError("--rows must be at least 20")
    output_dir = local_path(output_dir)
    output_path = output_dir / "measurements.csv"
    if output_path.exists():
        raise ValueError(f"Refusing to overwrite {output_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with output_path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["equipment", "timestamp", "temperature", "pressure", "target"])
        writer.writeheader()
        for index in range(rows):
            temperature = rng.gauss(70, 8)
            pressure = rng.gauss(4, 0.6)
            score = (temperature - 70) / 8 + (pressure - 4) / 0.6 + rng.gauss(0, 0.7)
            writer.writerow({
                "equipment": f"SIM-{index % 8 + 1:02d}",
                "timestamp": (start + timedelta(minutes=5 * index)).isoformat(),
                "temperature": "" if index % 23 == 0 else round(temperature, 3),
                "pressure": "" if index % 31 == 0 else round(pressure, 3),
                "target": int(score > 0.5),
            })
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, epilog="This example has no --overwrite option; choose a new output location.")
    parser.add_argument("--output-dir", type=Path, default=Path("data/demo"))
    parser.add_argument("--rows", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    try:
        print(make_demo_data(args.output_dir, args.rows, args.seed))
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
