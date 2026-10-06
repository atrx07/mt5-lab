"""Deterministically archive the six frozen Candidate-J Stage-1 prospective blocks.

The source folders remain local under data/prospective_4h/. This tool writes
reproducible .tar.gz archives plus a single index manifest under
`data/prospective_archives/`.

Scoring authority:
- score_ticks.csv is the authoritative scored stream.
- score_ticks.pre_recovery.csv, when present, is provenance only.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "prospective_4h"
DEFAULT_OUT = ROOT / "data" / "prospective_archives"

BLOCKS = (
    "20260928T150531Z",
    "20260929T132027Z",
    "20261001T171601Z",
    "20261002T071041Z",
    "20261002T132739Z",
    "20261005T132049Z",
)

REQUIRED = ("block_manifest.json", "warmup_ticks.csv", "score_ticks.csv")
PROVENANCE = ("score_ticks.pre_recovery.csv",)
CHUNK = 1024 * 1024


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def deterministic_tar_bytes(block_dir: Path, names: list[str]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tf:
        for name in sorted(names):
            path = block_dir / name
            data = path.read_bytes()
            info = tarfile.TarInfo(name=f"{block_dir.name}/{name}")
            info.size = len(data)
            info.mtime = 0
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mode = 0o644
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def write_deterministic_gzip(payload: bytes, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as gz:
            gz.write(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    source = args.source.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    index = {
        "schema_version": 1,
        "experiment": "candidate-j-stage1-fresh-prospective-validation",
        "status": "frozen-after-stage1-failure",
        "stage1_block_count": 6,
        "blocks": [],
        "notes": [
            "score_ticks.csv is the authoritative scored stream for each block.",
            "score_ticks.pre_recovery.csv, when present, is retained only as recovery provenance.",
            "The six blocks became outcome-known diagnostic/development data after Stage 1 scoring.",
            "They must not be relabeled as unseen evidence for any future candidate.",
        ],
    }

    for block_id in BLOCKS:
        block_dir = source / block_id
        if not block_dir.is_dir():
            raise SystemExit(f"Missing block directory: {block_dir}")

        missing = [name for name in REQUIRED if not (block_dir / name).is_file()]
        if missing:
            raise SystemExit(f"{block_id}: missing required files: {', '.join(missing)}")

        names = list(REQUIRED)
        for name in PROVENANCE:
            if (block_dir / name).is_file():
                names.append(name)

        file_records = []
        for name in sorted(names):
            path = block_dir / name
            file_records.append({
                "name": name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "role": (
                    "authoritative_scored_stream" if name == "score_ticks.csv"
                    else "recovery_provenance_only" if name == "score_ticks.pre_recovery.csv"
                    else "warmup_context" if name == "warmup_ticks.csv"
                    else "block_manifest"
                ),
            })

        payload = deterministic_tar_bytes(block_dir, names)
        archive_name = f"candidate_j_stage1_{block_id}.tar.gz"
        archive_path = out / archive_name
        write_deterministic_gzip(payload, archive_path)

        record = {
            "block_id": block_id,
            "archive": archive_name,
            "archive_bytes": archive_path.stat().st_size,
            "archive_sha256": sha256_file(archive_path),
            "files": file_records,
        }
        index["blocks"].append(record)

        print(f"{block_id}: {archive_name}")
        print(f"  bytes  {record['archive_bytes']:,}")
        print(f"  sha256 {record['archive_sha256']}")

    index_path = out / "candidate_j_stage1_index.json"
    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(f"\nIndex: {index_path}")
    print(f"Index SHA256: {sha256_file(index_path)}")


if __name__ == "__main__":
    main()
