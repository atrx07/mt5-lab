# Data — archival policy and capture workflow

## Policy

- Curated archives live in `data/raw/` as plain `.csv` with a manifest in
  `data/manifests/`. (Plain CSV, not gzip: the GitHub push path cannot carry
  binary, and daily-bar files are KB-scale. Revisit if tick archives grow
  large — git-lfs or chunked CSV.) Raw uncurated captures are NEVER committed
  (`.gitignore`).
- Synthetic data is prefixed `SYNTHETIC_` and never mixed with real captures.
- xau-lab MT5 ticks are a different instrument/venue and are NOT valid data here.
- At capture time, split into **dev** and **sealed holdout** archives. The
  holdout is never opened during development. One shot, per lab rules.

## Manifest fields (minimum)

schema version, dataset ID, instrument, contract, source/platform/exporter,
capture window (UTC + IST), row count, first/last timestamp, column list,
archive path, archive SHA-256, provenance/contamination notes.

## Capture workflow (Phase 1)

1. Broker websocket (Kite Connect default) streams GOLDPETAL bid/ask ticks.
2. `tools/capture_ticks.py` appends to a local store with session markers
   (9:00-23:55 IST), rollover-day flags, and circuit-halt flags.
3. Weekly: curate into `<instrument>_<contract>_ticks_<range>.csv` +
   manifest; verify SHA-256; commit manifest + archive.
4. Target before Phase 3: 4+ weeks of ticks, dev/holdout split at capture.

## Column contract (ticks)

`ts` (epoch sec, monotonic), `bid`, `ask` (Rs per gram, 2 dp).
`mid` is derived, never stored as a fill price.
