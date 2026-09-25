"""Restore a manifest-tracked gzip dataset without overwriting existing raw data."""

import argparse
import gzip
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    archive = ROOT / manifest["archive"]["relative_path"]
    output = ROOT / manifest["raw"]["filename"]
    if output.exists():
        raise RuntimeError(f"raw output already exists: {output}")
    if sha256(archive) != manifest["archive"]["sha256"]:
        raise RuntimeError("archive SHA-256 mismatch")
    created = False
    try:
        with output.open("xb") as target:
            created = True
            with gzip.open(archive, "rb") as source:
                shutil.copyfileobj(source, target)
        if output.stat().st_size != manifest["raw"]["bytes"] or sha256(output) != manifest["raw"]["sha256"]:
            raise RuntimeError("restored raw dataset size/SHA-256 mismatch")
    except BaseException:
        if created:
            output.unlink(missing_ok=True)
        raise
    print(output)


if __name__ == "__main__":
    main()
