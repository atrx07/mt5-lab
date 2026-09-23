"""Create a deterministic gzip archive for a manifest-tracked research dataset."""

import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path


CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_csv", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()

    raw = args.raw_csv.resolve()
    manifest_path = args.manifest.resolve()

    if not raw.is_file():
        raise SystemExit(f"Raw CSV not found: {raw}")

    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    expected_raw_sha = data["raw"]["sha256"]
    expected_raw_bytes = int(data["raw"]["bytes"])
    actual_raw_bytes = raw.stat().st_size

    print(f"Raw bytes:  {actual_raw_bytes:,}")
    if actual_raw_bytes != expected_raw_bytes:
        raise SystemExit(
            f"Raw size mismatch: expected {expected_raw_bytes:,}, got {actual_raw_bytes:,}"
        )

    print("Hashing raw CSV...")
    actual_raw_sha = sha256_file(raw)
    if actual_raw_sha != expected_raw_sha:
        raise SystemExit(
            "Raw SHA-256 mismatch\n"
            f"expected: {expected_raw_sha}\n"
            f"actual:   {actual_raw_sha}"
        )

    print("Raw SHA-256 verified.")

    repo_root = manifest_path.parents[2]
    archive_rel = Path(data["archive"]["relative_path"])
    archive_path = repo_root / archive_rel
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    level = int(data["archive"].get("compression_level", 9))

    print(f"Writing {archive_path} ...")
    with raw.open("rb") as src, archive_path.open("wb") as dst:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=dst,
            compresslevel=level,
            mtime=0,
        ) as gz:
            shutil.copyfileobj(src, gz, length=CHUNK_SIZE)

    archive_bytes = archive_path.stat().st_size
    archive_sha = sha256_file(archive_path)

    data["archive"]["bytes"] = archive_bytes
    data["archive"]["sha256"] = archive_sha
    data["archive"]["status"] = "archived"

    manifest_path.write_text(
        json.dumps(data, indent=2) + "\n",
        encoding="utf-8",
    )

    ratio = archive_bytes / actual_raw_bytes
    print()
    print("Archive complete.")
    print(f"Archive bytes:  {archive_bytes:,}")
    print(f"Compression:    {ratio:.2%} of raw")
    print(f"Archive SHA256: {archive_sha}")
    print(f"Manifest:       {manifest_path}")


if __name__ == "__main__":
    main()
