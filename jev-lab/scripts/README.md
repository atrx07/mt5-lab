# Scripts

`probe_jev.py` accepts a JSON file with `state`, `instructions`, `criteria`, and optional pinned `model`. By default it validates locally and prints only the request hash, model, and option names. With `--send`, it makes one API call using `TYPESAFE_API_KEY` from the environment. It never places a market order.

Example file contents for local validation:

```json
{
  "model": "jev-1.13.0",
  "state": {"market": "synthetic", "candidate": "buy"},
  "instructions": "Should this synthetic setup be reviewed?",
  "criteria": {"review": "Review the setup", "skip": "Do nothing"}
}
```

```powershell
python scripts/probe_jev.py tests\fixtures\synthetic_choice.json
python scripts/probe_jev.py path\to\your_request.json --send
```

Put future small CLI entry points and acquisition tools here. Reusable trading, replay, model, and risk logic belongs in `src/jev_lab/`. Each script should document inputs, outputs, execution mode, and a reproducible command in its matching experiment record.

`capture_binance_klines.py` reads public BTC/USDT 30-minute candles into ignored `data/raw/` and writes a versioned SHA-256 manifest. `replay_baseline.py` verifies that manifest, evaluates only the first 80% with the frozen paper rule and comparators, and writes one durable backtest bundle. Neither script has an order endpoint.

```powershell
python scripts/capture_binance_klines.py
python scripts/replay_baseline.py
```
