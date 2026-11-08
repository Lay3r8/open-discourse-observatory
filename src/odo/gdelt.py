from __future__ import annotations

import csv
import hashlib
import json
import shutil
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

GDELT_EVENT_COLUMNS = [
    "GLOBALEVENTID", "SQLDATE", "MonthYear", "Year", "FractionDate",
    "Actor1Code", "Actor1Name", "Actor1CountryCode", "Actor1KnownGroupCode",
    "Actor1EthnicCode", "Actor1Religion1Code", "Actor1Religion2Code", "Actor1Type1Code",
    "Actor1Type2Code", "Actor1Type3Code", "Actor2Code", "Actor2Name", "Actor2CountryCode",
    "Actor2KnownGroupCode", "Actor2EthnicCode", "Actor2Religion1Code", "Actor2Religion2Code",
    "Actor2Type1Code", "Actor2Type2Code", "Actor2Type3Code", "IsRootEvent", "EventCode",
    "EventBaseCode", "EventRootCode", "QuadClass", "GoldsteinScale", "NumMentions",
    "NumSources", "NumArticles", "AvgTone", "Actor1Geo_Type", "Actor1Geo_FullName",
    "Actor1Geo_CountryCode", "Actor1Geo_ADM1Code", "Actor1Geo_ADM2Code", "Actor1Geo_Lat",
    "Actor1Geo_Long", "Actor1Geo_FeatureID", "Actor2Geo_Type", "Actor2Geo_FullName",
    "Actor2Geo_CountryCode", "Actor2Geo_ADM1Code", "Actor2Geo_ADM2Code", "Actor2Geo_Lat",
    "Actor2Geo_Long", "Actor2Geo_FeatureID", "ActionGeo_Type", "ActionGeo_FullName",
    "ActionGeo_CountryCode", "ActionGeo_ADM1Code", "ActionGeo_ADM2Code", "ActionGeo_Lat",
    "ActionGeo_Long", "ActionGeo_FeatureID", "DATEADDED", "SOURCEURL",
]


@dataclass(frozen=True)
class GdeltArtifact:
    source_path: Path
    sha256: str
    row_count: int
    parquet_path: Path | None = None


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_export_tsv(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        for raw in reader:
            if not raw:
                continue
            padded = raw[: len(GDELT_EVENT_COLUMNS)] + [""] * max(0, len(GDELT_EVENT_COLUMNS) - len(raw))
            rows.append(dict(zip(GDELT_EVENT_COLUMNS, padded, strict=True)))
    return rows


def download_export(timestamp: str, raw_root: Path) -> Path:
    dt = datetime.strptime(timestamp, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    directory = raw_root / "gdelt" / "events" / f"date={dt:%Y-%m-%d}" / f"hour={dt:%H}"
    directory.mkdir(parents=True, exist_ok=True)
    zip_path = directory / f"{timestamp}.export.CSV.zip"
    if zip_path.exists():
        return zip_path
    url = f"https://data.gdeltproject.org/gdeltv2/{timestamp}.export.CSV.zip"
    with urllib.request.urlopen(url, timeout=60) as response, zip_path.open("wb") as output:
        shutil.copyfileobj(response, output)
    return zip_path


def extract_zip(zip_path: Path) -> Path:
    with zipfile.ZipFile(zip_path) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]
        if len(names) != 1:
            raise ValueError(f"Expected one GDELT export file, found {len(names)}")
        output = zip_path.with_suffix("")
        with archive.open(names[0]) as src, output.open("wb") as dst:
            shutil.copyfileobj(src, dst)
    return output


def to_parquet(tsv_path: Path, bronze_root: Path, timestamp: str) -> GdeltArtifact:
    import polars as pl

    dt = datetime.strptime(timestamp, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    target_dir = bronze_root / "gdelt" / "events" / f"date={dt:%Y-%m-%d}" / f"hour={dt:%H}"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{timestamp}.parquet"

    frame = pl.read_csv(
        tsv_path,
        separator="\t",
        has_header=False,
        new_columns=GDELT_EVENT_COLUMNS,
        truncate_ragged_lines=True,
        infer_schema_length=0,
    )
    frame.write_parquet(target, compression="zstd")

    manifest = {
        "timestamp": timestamp,
        "source_path": str(tsv_path),
        "source_sha256": sha256_file(tsv_path),
        "rows": frame.height,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    target.with_suffix(".manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return GdeltArtifact(tsv_path, manifest["source_sha256"], frame.height, target)
