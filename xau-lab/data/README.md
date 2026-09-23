# XAUUSD research datasets

This directory stores curated, reproducible market-data artifacts used by the xau-lab experiments.

## Policy

- Raw uncompressed broker exports stay out of Git.
- A small curated dataset may be stored as a lossless `.csv.gz` archive.
- Every archived dataset must have a manifest containing the exact raw SHA-256, byte size, row count, time range, archive SHA-256, compression settings, and experiment references.
- Larger or recurring datasets should move to Git LFS or external object storage rather than accumulating in normal Git history.

## Current dataset

The seven-day MT5 XAUUSD export used by experiments 07 and 08 is described by:

`manifests/xau_ticks_7d_2026-09-16_to_2026-09-23.json`

The intended archive path is:

`raw/xau_ticks_7d_2026-09-16_to_2026-09-23.csv.gz`

## Archive it after pulling the repo

From `xau-lab/`, with the original `xau_ticks_7d.csv` present:

```powershell
python scripts\archive_dataset.py xau_ticks_7d.csv data\manifests\xau_ticks_7d_2026-09-16_to_2026-09-23.json
```

The helper will:

1. verify the raw CSV SHA-256;
2. write a deterministic gzip archive into `data/raw/`;
3. compute the archive SHA-256 and size;
4. update the manifest automatically.

Then:

```powershell
git add data\raw\xau_ticks_7d_2026-09-16_to_2026-09-23.csv.gz
git add data\manifests\xau_ticks_7d_2026-09-16_to_2026-09-23.json
git commit -m "Archive seven-day XAUUSD broker dataset"
git push
```

Do **not** add the 220 MB raw CSV itself.
