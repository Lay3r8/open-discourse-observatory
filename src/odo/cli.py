from __future__ import annotations

import argparse
from pathlib import Path

from odo.config import Settings
from odo.gdelt import download_export, extract_zip, to_parquet
from odo.import_pilot import import_pilot
from odo.migrations import migrate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="odo")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate")
    sub.add_parser("import-pilot")

    gdelt_download = sub.add_parser("gdelt-download")
    gdelt_download.add_argument("timestamp", help="GDELT v2 timestamp, e.g. 20260101000000")

    gdelt_file = sub.add_parser("gdelt-file")
    gdelt_file.add_argument("path", type=Path)
    gdelt_file.add_argument("--timestamp", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings.from_env()

    if args.command == "migrate":
        applied = migrate()
        print(f"Applied {len(applied)} migration(s): {', '.join(applied) or 'none'}")
        return 0

    if args.command == "import-pilot":
        reference_dir = settings.data_dir / "reference" / "pilot-v0.1"
        counts = import_pilot(reference_dir)
        print(counts)
        return 0

    if args.command == "gdelt-download":
        zip_path = download_export(args.timestamp, settings.data_dir / "raw")
        tsv_path = extract_zip(zip_path)
        artifact = to_parquet(tsv_path, settings.data_dir / "bronze", args.timestamp)
        print(artifact)
        return 0

    if args.command == "gdelt-file":
        artifact = to_parquet(args.path, settings.data_dir / "bronze", args.timestamp)
        print(artifact)
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
