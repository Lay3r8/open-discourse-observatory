from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from odo.config import Settings
from odo.db import connection
from odo.discovery import QueryEstimate, discover_range, discovery_stats
from odo.gdelt import download_export, extract_zip, to_parquet
from odo.import_pilot import import_pilot
from odo.migrations import migrate
from odo.storage import GIB, collect_storage_status, render_storage_status


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected YYYY-MM-DD") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="odo")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("migrate")
    sub.add_parser("import-pilot")
    sub.add_parser("db-check")

    storage = sub.add_parser("storage")
    storage_sub = storage.add_subparsers(dest="storage_command", required=True)
    storage_sub.add_parser("status")

    discover = sub.add_parser("discover")
    discover.add_argument("--start", type=_date, required=True)
    discover.add_argument("--end", type=_date, required=True)
    discover.add_argument(
        "--execute",
        action="store_true",
        help="execute BigQuery and write local data; default is dry-run only",
    )

    stats = sub.add_parser("discovery-stats")
    stats.add_argument("--start", type=_date, required=True)
    stats.add_argument("--end", type=_date, required=True)

    gdelt_download = sub.add_parser("gdelt-download")
    gdelt_download.add_argument("timestamp", help="GDELT v2 timestamp, e.g. 20260101000000")

    gdelt_file = sub.add_parser("gdelt-file")
    gdelt_file.add_argument("path", type=Path)
    gdelt_file.add_argument("--timestamp", required=True)

    return parser


def _print_discovery_results(results: list[dict[str, object] | QueryEstimate]) -> None:
    for result in results:
        if isinstance(result, QueryEstimate):
            state = "SAFE" if result.safe else "BLOCKED"
            print(
                f"{result.batch_date.isoformat()} "
                f"estimated={result.total_bytes_processed / GIB:.3f} GiB "
                f"limit={result.max_bytes_billed / GIB:.3f} GiB {state}"
            )
            continue

        print(
            f"{result['batch_date']} "
            f"candidates={result['candidate_rows']} "
            f"negative_control={result['negative_control_rows']} "
            f"unique_urls={result['unique_urls']} "
            f"unique_titles={result['unique_titles']} "
            f"processed={int(result['query_bytes_processed']) / GIB:.3f} GiB "
            f"billed={int(result['query_bytes_billed']) / GIB:.3f} GiB"
        )


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

    if args.command == "db-check":
        with connection(settings) as conn:
            incidents = conn.execute("select count(*) from research.incident").fetchone()[0]
            sources = conn.execute("select count(*) from research.source").fetchone()[0]
            coding = conn.execute("select count(*) from research.coding_decision").fetchone()[0]
            batches = conn.execute("select count(*) from staging.discovery_batch").fetchone()[0]
            candidate_docs = conn.execute(
                "select count(*) from staging.candidate_document"
            ).fetchone()[0]
        print(
            f"incidents={incidents} sources={sources} coding_decisions={coding} "
            f"discovery_batches={batches} candidate_documents={candidate_docs}"
        )
        return 0

    if args.command == "storage" and args.storage_command == "status":
        status = collect_storage_status(settings)
        print(render_storage_status(settings, status))
        return 2 if status.state == "BLOCKED" else 0

    if args.command == "discover":
        results = discover_range(
            settings,
            args.start,
            args.end,
            execute=args.execute,
        )
        _print_discovery_results(results)
        if not args.execute and any(
            isinstance(result, QueryEstimate) and not result.safe for result in results
        ):
            return 2
        return 0

    if args.command == "discovery-stats":
        stats = discovery_stats(settings, args.start, args.end)
        for key, value in stats.items():
            if key.endswith("_bytes"):
                print(f"{key}={int(value) / GIB:.3f} GiB")
            else:
                print(f"{key}={value}")
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
