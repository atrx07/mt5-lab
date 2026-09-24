# Data contract

Capture originals in `raw/`, generate reproducible features and response caches in `derived/`, and record each source in `manifests/<dataset-id>.json` before citing a result.

The first frozen public BTC/USDT capture is indexed by [2026-09-24-00-btc-spot-baseline.json](manifests/2026-09-24-00-btc-spot-baseline.json). Its raw 90-day candle file is local and Git-ignored; do not substitute a newly captured window for this hash.

Never overwrite an original capture. Preserve event timestamps and acquisition timestamps separately, with timezone and clock-offset caveats. Record bid/ask or order-book fields, venue and instrument identifiers, missing data, duplicate events, gaps, and source licensing. Hash original and archived bytes with SHA-256. The required manifest fields and storage rules are defined in [STRUCTURE.md](../STRUCTURE.md#data-and-provenance).

Raw and derived files are ignored by Git. A result bundle must still point to a durable, reproducible data source; an untracked local file alone is not sufficient long-term provenance.
