#!/usr/bin/env python3
"""MCX tick capture — SPECIFIED, not yet wired to credentials.

Interface contract for Phase 1. This script defines EXACTLY what the capture
pipeline must do; the broker-credential wiring is a separate, explicitly
authorized step (credentials live in .env, never in git).

Pipeline:
  broker websocket (Kite Connect default) --ticks--> local append-only store
      --> weekly curation into data/raw/<instrument>_<contract>_ticks_<range>.csv.gz
      --> manifest in data/manifests/

Column contract: ts (epoch sec, monotonic), bid, ask (Rs/gram, 2dp).
Session markers: 09:00-23:55 IST, rollover-day and circuit-halt flags.

Run:
  python tools/capture_ticks.py --dry-run     # validates interface, no creds needed
  python tools/capture_ticks.py               # requires .env (fails loudly otherwise)

.env (NEVER committed):
  BROKER=kite
  KITE_API_KEY=...
  KITE_API_SECRET=...
  KITE_ACCESS_TOKEN=...   # refreshed daily per broker flow
"""

import argparse
import os
import sys


def load_creds() -> dict:
    required = ["KITE_API_KEY", "KITE_API_SECRET", "KITE_ACCESS_TOKEN"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise RuntimeError(
            f"capture_ticks: missing credentials in environment: {missing}. "
            "See .env spec in this file's docstring. Refusing to run."
        )
    try:
        import kiteconnect  # noqa: F401
    except ImportError:
        raise RuntimeError(
            "capture_ticks: `kiteconnect` not installed. "
            "`pip install kiteconnect` (add to requirements.txt when wired)."
        )
    return {k: os.environ[k] for k in required}


def dry_run() -> int:
    print("capture_ticks --dry-run")
    print("  interface: KiteTicker websocket -> append {ts, bid, ask} per tick")
    print("  session:   09:00-23:55 IST, rollover + circuit flags")
    print("  output:    data/raw/<instrument>_<contract>_ticks_<range>.csv.gz + manifest")
    print("  status:    SPECIFIED ONLY — no credentials wired, nothing captured.")
    print("  next:      authorize broker API wiring, then implement _run_live().")
    return 0


def _run_live() -> int:
    creds = load_creds()
    # --- TO BE IMPLEMENTED against real credentials ---
    # 1. KiteTicker(api_key, access_token) with static-IP origin (SEBI framework)
    # 2. subscribe(GOLDPETAL instrument_token, mode=FULL) for bid/ask depth-1
    # 3. on_ticks: append (ts, bid, ask); on session end: roll file, write manifest
    # 4. reconnect with backoff; log gaps as contamination notes in manifest
    raise NotImplementedError(
        "_run_live: credential wiring is a separate authorized step. "
        f"Loaded key {creds['KITE_API_KEY'][:4]}... but live capture is not "
        "implemented until the broker/API choice is finalized with the user."
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    return dry_run() if a.dry_run else _run_live()


if __name__ == "__main__":
    sys.exit(main())
