"""Run the controlled M6C historical nflverse PBP compatibility checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import cast

import polars as pl

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from daily_nfl.persistence import apply_migrations, open_database  # noqa: E402
from daily_nfl.providers import (  # noqa: E402
    NFLVERSE_DESCRIPTOR,
    AcquisitionRequest,
    AcquisitionService,
    DatasetKind,
    FileSystemRawEvidenceStore,
    NflverseAdapter,
    NflverseHttpLoader,
    record_stored_acquisition,
    resolve_nflverse_assets,
)
from daily_nfl.validation import (  # noqa: E402
    M6C_CONTRACT_VERSION,
    M6C_VALIDATOR_VERSION,
    M6CStatus,
    classify_m6c_validation,
    document_sha256,
    validate_nflverse_pbp_rows,
)

SENTINEL_SEASONS = (1999, 2005, 2010, 2015, 2020, 2025)
MIN_SEASON = 1999
MAX_COMPLETED_SEASON = 2025
EXECUTION_MODES = frozenset(
    {
        "VALIDATED",
        "REVALIDATED",
        "RESUMED_VALIDATION",
    }
)
RAW_RESOLUTION_MODES = frozenset({"REUSED_RAW", "ACQUIRED"})


@dataclass(frozen=True, slots=True)
class RawSeasonEvidence:
    season: int
    evidence_id: str
    evidence_observation_id: str
    sha256: str
    raw_path: Path
    source_uri: str
    size_bytes: int
    acquisition_mode: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("local-data/m6c/m6c-history.db"),
        help="SQLite evidence ledger for M6C",
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=Path("local-data/m6c/raw"),
        help="Root directory for immutable raw PBP evidence",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("local-data/m6c/validation"),
        help="Directory for per-season summaries and aggregate manifest",
    )
    parser.add_argument(
        "--gate",
        choices=("sentinel", "full"),
        default="sentinel",
        help="Sentinel era scan or full 1999-2025 sweep",
    )
    parser.add_argument("--seasons", nargs="+", type=int)
    parser.add_argument("--start-season", type=int)
    parser.add_argument("--end-season", type=int)
    parser.add_argument(
        "--revalidate",
        action="store_true",
        help="Re-run normalization from stored raw bytes even when a valid summary exists",
    )
    parser.add_argument(
        "--force-reacquire",
        action="store_true",
        help="Acquire the exact upstream asset again and record a new acquisition observation",
    )
    parser.add_argument("--timeout", type=float, default=120.0)
    return parser.parse_args()


def _resolve_seasons(args: argparse.Namespace) -> tuple[int, ...]:
    if args.seasons and (args.start_season is not None or args.end_season is not None):
        raise ValueError("--seasons cannot be combined with --start-season/--end-season")

    if args.seasons:
        seasons = tuple(int(value) for value in args.seasons)
    elif args.start_season is not None or args.end_season is not None:
        start = int(args.start_season if args.start_season is not None else MIN_SEASON)
        end = int(
            args.end_season if args.end_season is not None else MAX_COMPLETED_SEASON
        )
        if end < start:
            raise ValueError("end season cannot precede start season")
        seasons = tuple(range(start, end + 1))
    elif args.gate == "full":
        seasons = tuple(range(MIN_SEASON, MAX_COMPLETED_SEASON + 1))
    else:
        seasons = SENTINEL_SEASONS

    if len(seasons) != len(set(seasons)):
        raise ValueError("requested M6C seasons cannot contain duplicates")
    if any(season < MIN_SEASON or season > MAX_COMPLETED_SEASON for season in seasons):
        raise ValueError(
            f"M6C historical seasons must be between {MIN_SEASON} and "
            f"{MAX_COMPLETED_SEASON} inclusive"
        )
    return seasons


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _expected_source_uri(season: int) -> str:
    assets = resolve_nflverse_assets(
        AcquisitionRequest(dataset=DatasetKind.PLAY_BY_PLAY, seasons=(season,))
    )
    if len(assets) != 1:
        raise RuntimeError("one-season M6C acquisition must resolve exactly one raw asset")
    return assets[0].url


def _lookup_existing_raw(
    connection: sqlite3.Connection,
    *,
    raw_root: Path,
    season: int,
) -> RawSeasonEvidence | None:
    source_uri = _expected_source_uri(season)
    row = connection.execute(
        """
        SELECT re.evidence_id, re.sha256, re.object_path,
               reo.evidence_observation_id
        FROM raw_evidence re
        JOIN raw_evidence_observations reo
          ON reo.evidence_id = re.evidence_id
        WHERE re.provider_id = ?
          AND re.endpoint_category = ?
          AND re.source_uri = ?
          AND reo.dataset = ?
        ORDER BY reo.ingested_at DESC, reo.evidence_observation_id DESC
        LIMIT 1
        """,
        (
            NFLVERSE_DESCRIPTOR.provider_id,
            DatasetKind.PLAY_BY_PLAY.value,
            source_uri,
            DatasetKind.PLAY_BY_PLAY.value,
        ),
    ).fetchone()
    if row is None:
        return None

    raw_path = raw_root / Path(str(row[2]))
    if not raw_path.is_file():
        raise RuntimeError(
            f"stored M6C raw metadata exists but object is missing: {raw_path}"
        )
    actual_sha256 = _sha256_file(raw_path)
    expected_sha256 = str(row[1])
    if actual_sha256 != expected_sha256:
        raise RuntimeError(
            f"stored M6C raw checksum mismatch for season {season}: "
            f"{actual_sha256} != {expected_sha256}"
        )

    return RawSeasonEvidence(
        season=season,
        evidence_id=str(row[0]),
        evidence_observation_id=str(row[3]),
        sha256=expected_sha256,
        raw_path=raw_path,
        source_uri=source_uri,
        size_bytes=raw_path.stat().st_size,
        acquisition_mode="REUSED_RAW",
    )


def _acquire_raw(
    *,
    connection: sqlite3.Connection,
    service: AcquisitionService,
    adapter: NflverseAdapter,
    raw_root: Path,
    season: int,
) -> RawSeasonEvidence:
    request = AcquisitionRequest(dataset=DatasetKind.PLAY_BY_PLAY, seasons=(season,))
    acquisition = service.acquire(adapter, request)
    if len(acquisition.evidence) != 1:
        raise RuntimeError("one-season M6C acquisition must return exactly one evidence object")
    record_stored_acquisition(connection, acquisition)
    connection.commit()

    evidence = acquisition.evidence[0]
    raw_path = raw_root / evidence.artifact.relative_path
    actual_sha256 = _sha256_file(raw_path)
    if actual_sha256 != evidence.artifact.sha256:
        raise RuntimeError(f"fresh M6C raw checksum mismatch for season {season}")
    return RawSeasonEvidence(
        season=season,
        evidence_id=evidence.artifact.evidence_id,
        evidence_observation_id=evidence.evidence_observation_id,
        sha256=evidence.artifact.sha256,
        raw_path=raw_path,
        source_uri=evidence.payload.source_uri or _expected_source_uri(season),
        size_bytes=evidence.artifact.size_bytes,
        acquisition_mode="ACQUIRED",
    )


def _ensure_raw(
    *,
    connection: sqlite3.Connection,
    service: AcquisitionService,
    adapter: NflverseAdapter,
    raw_root: Path,
    season: int,
    force_reacquire: bool,
) -> RawSeasonEvidence:
    if not force_reacquire:
        existing = _lookup_existing_raw(connection, raw_root=raw_root, season=season)
        if existing is not None:
            return existing
    return _acquire_raw(
        connection=connection,
        service=service,
        adapter=adapter,
        raw_root=raw_root,
        season=season,
    )


def _summary_path(output_root: Path, season: int) -> Path:
    return output_root / f"season-{season}.json"


def _atomic_write_json(path: Path, document: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(document, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def _valid_resumable_summary(
    path: Path,
    *,
    season: int,
    raw: RawSeasonEvidence,
) -> dict[str, object] | None:
    if not path.is_file():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return None
    document = cast(dict[str, object], loaded)
    stored_integrity = document.get("summary_sha256")
    if not isinstance(stored_integrity, str):
        return None
    content = dict(document)
    content.pop("summary_sha256", None)
    if document_sha256(content) != stored_integrity:
        return None
    required = {
        "contract_version": M6C_CONTRACT_VERSION,
        "validator_version": M6C_VALIDATOR_VERSION,
        "season": season,
        "evidence_id": raw.evidence_id,
        "raw_sha256": raw.sha256,
        "parser_version": NFLVERSE_DESCRIPTOR.parser_version,
        "validation_status": M6CStatus.PASS.value,
    }
    if any(document.get(key) != value for key, value in required.items()):
        return None
    return document


def _validate_raw_season(
    *,
    raw: RawSeasonEvidence,
    previous_summary: dict[str, object] | None,
) -> dict[str, object]:
    frame = pl.read_parquet(raw.raw_path)
    rows = cast(list[dict[str, object]], frame.to_dicts())
    validation = validate_nflverse_pbp_rows(
        rows,
        row_count=frame.height,
        column_count=frame.width,
        id_prefix=f"m6c_{raw.season}",
    )
    validation_fingerprint = document_sha256(validation)
    status, reasons = classify_m6c_validation(validation)

    previous_fingerprint = None
    reproducibility_match = None
    if previous_summary is not None:
        value = previous_summary.get("validation_fingerprint")
        if isinstance(value, str):
            previous_fingerprint = value
            reproducibility_match = value == validation_fingerprint
            if not reproducibility_match:
                status = M6CStatus.FAIL
                reasons = tuple(
                    sorted(
                        set(
                            (*reasons, "revalidation fingerprint differs from prior stored summary")
                        )
                    )
                )

    document: dict[str, object] = {
        "contract_version": M6C_CONTRACT_VERSION,
        "validator_version": M6C_VALIDATOR_VERSION,
        "season": raw.season,
        "provider_id": NFLVERSE_DESCRIPTOR.provider_id,
        "parser_version": NFLVERSE_DESCRIPTOR.parser_version,
        "nflreadpy_version": version("nflreadpy"),
        "polars_version": pl.__version__,
        "source_uri": raw.source_uri,
        "evidence_id": raw.evidence_id,
        "evidence_observation_id": raw.evidence_observation_id,
        "raw_sha256": raw.sha256,
        "raw_size_bytes": raw.size_bytes,
        "raw_object_path": raw.raw_path.as_posix(),
        "acquisition_mode": raw.acquisition_mode,
        "validation_status": status.value,
        "validation_reasons": list(reasons),
        "validation_fingerprint": validation_fingerprint,
        "previous_validation_fingerprint": previous_fingerprint,
        "reproducibility_match": reproducibility_match,
        "validation": validation,
    }
    document["summary_sha256"] = document_sha256(document)
    return document


def _required_int(document: dict[str, object], key: str) -> int:
    value = document.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{key} must be an integer")
    return value


def _status_rank(value: str) -> int:
    return {
        M6CStatus.PASS.value: 0,
        M6CStatus.REVIEW_REQUIRED.value: 1,
        M6CStatus.FAIL.value: 2,
    }[value]


def _season_manifest_entry(
    summary: dict[str, object],
    *,
    execution_mode: str,
    raw_resolution_mode: str,
) -> dict[str, object]:
    if execution_mode not in EXECUTION_MODES:
        raise ValueError(f"unsupported M6C execution mode: {execution_mode!r}")
    if raw_resolution_mode not in RAW_RESOLUTION_MODES:
        raise ValueError(
            f"unsupported M6C raw resolution mode: {raw_resolution_mode!r}"
        )

    return {
        "season": summary["season"],
        "status": summary["validation_status"],
        "reasons": summary["validation_reasons"],
        "evidence_id": summary["evidence_id"],
        "evidence_observation_id": summary["evidence_observation_id"],
        "raw_sha256": summary["raw_sha256"],
        "raw_size_bytes": summary["raw_size_bytes"],
        "validation_acquisition_mode": summary["acquisition_mode"],
        "raw_resolution_mode": raw_resolution_mode,
        "execution_mode": execution_mode,
        "validation_fingerprint": summary["validation_fingerprint"],
        "reproducibility_match": summary["reproducibility_match"],
    }


def _build_manifest(
    *,
    seasons: tuple[int, ...],
    summaries: list[dict[str, object]],
    execution_modes: list[str],
    raw_resolution_modes: list[str],
    database: Path,
    raw_root: Path,
    output_root: Path,
    schema_version: int,
) -> dict[str, object]:
    if not (
        len(summaries)
        == len(execution_modes)
        == len(raw_resolution_modes)
    ):
        raise ValueError(
            "M6C summaries, execution modes, and raw resolution modes "
            "must have identical lengths"
        )

    statuses = [str(summary["validation_status"]) for summary in summaries]
    overall_status = max(statuses, key=_status_rank)
    validations = [cast(dict[str, object], summary["validation"]) for summary in summaries]

    totals = {
        "row_count": sum(_required_int(item, "row_count") for item in validations),
        "extracted_and_normalized_count": sum(
            _required_int(item, "extracted_and_normalized_count") for item in validations
        ),
        "extraction_error_count": sum(
            _required_int(item, "extraction_error_count") for item in validations
        ),
        "normalization_error_count": sum(
            _required_int(item, "normalization_error_count") for item in validations
        ),
        "next_state_adjacent_validated": sum(
            _required_int(item, "next_state_adjacent_validated") for item in validations
        ),
        "next_state_nonadjacent_skipped": sum(
            _required_int(item, "next_state_nonadjacent_skipped") for item in validations
        ),
        "next_state_error_count": sum(
            _required_int(item, "next_state_error_count") for item in validations
        ),
        "raw_size_bytes": sum(_required_int(summary, "raw_size_bytes") for summary in summaries),
    }
    manifest: dict[str, object] = {
        "contract_version": M6C_CONTRACT_VERSION,
        "validator_version": M6C_VALIDATOR_VERSION,
        "provider_id": NFLVERSE_DESCRIPTOR.provider_id,
        "parser_version": NFLVERSE_DESCRIPTOR.parser_version,
        "schema_version": schema_version,
        "requested_seasons": list(seasons),
        "season_count": len(seasons),
        "overall_status": overall_status,
        "database": str(database),
        "raw_root": str(raw_root),
        "output_root": str(output_root),
        "totals": totals,
        "seasons": [
            _season_manifest_entry(
                summary,
                execution_mode=execution_mode,
                raw_resolution_mode=raw_resolution_mode,
            )
            for summary, execution_mode, raw_resolution_mode in zip(
                summaries,
                execution_modes,
                raw_resolution_modes,
                strict=True,
            )
        ],
    }
    manifest["manifest_sha256"] = document_sha256(manifest)
    return manifest


def main() -> int:
    args = parse_args()
    seasons = _resolve_seasons(args)
    database: Path = args.database
    raw_root: Path = args.raw_root
    output_root: Path = args.output_root

    adapter = NflverseAdapter(
        loader=NflverseHttpLoader(
            user_agent="Daily-NFL/0.1 M6C-historical-checkpoint",
            timeout_seconds=float(args.timeout),
        )
    )
    service = AcquisitionService(FileSystemRawEvidenceStore(raw_root))
    summaries: list[dict[str, object]] = []
    execution_modes: list[str] = []
    raw_resolution_modes: list[str] = []

    with open_database(database) as connection:
        schema_version = apply_migrations(connection)
        connection.commit()
        for season in seasons:
            raw = _ensure_raw(
                connection=connection,
                service=service,
                adapter=adapter,
                raw_root=raw_root,
                season=season,
                force_reacquire=bool(args.force_reacquire),
            )
            path = _summary_path(output_root, season)
            previous = _valid_resumable_summary(path, season=season, raw=raw)
            if previous is not None and not args.revalidate:
                summary = previous
                execution_mode = "RESUMED_VALIDATION"
            else:
                summary = _validate_raw_season(raw=raw, previous_summary=previous)
                execution_mode = (
                    "REVALIDATED"
                    if previous is not None
                    else "VALIDATED"
                )
                _atomic_write_json(path, summary)

            summaries.append(summary)
            execution_modes.append(execution_mode)
            raw_resolution_modes.append(raw.acquisition_mode)

            concise = {
                "season": season,
                "status": summary["validation_status"],
                "validation_acquisition_mode": summary["acquisition_mode"],
                "raw_resolution_mode": raw.acquisition_mode,
                "execution_mode": execution_mode,
                "validation_fingerprint": summary["validation_fingerprint"],
            }
            print(json.dumps(concise, sort_keys=True))

    manifest = _build_manifest(
        seasons=seasons,
        summaries=summaries,
        execution_modes=execution_modes,
        raw_resolution_modes=raw_resolution_modes,
        database=database,
        raw_root=raw_root,
        output_root=output_root,
        schema_version=schema_version,
    )
    label = (
        "full"
        if seasons == tuple(range(MIN_SEASON, MAX_COMPLETED_SEASON + 1))
        else "selected"
    )
    manifest_path = output_root / f"m6c-manifest-{label}.json"
    _atomic_write_json(manifest_path, manifest)

    result = {
        "overall_status": manifest["overall_status"],
        "season_count": manifest["season_count"],
        "requested_seasons": manifest["requested_seasons"],
        "totals": manifest["totals"],
        "schema_version": schema_version,
        "manifest": str(manifest_path),
        "manifest_sha256": manifest["manifest_sha256"],
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if manifest["overall_status"] == M6CStatus.PASS.value else 2


if __name__ == "__main__":
    raise SystemExit(main())
