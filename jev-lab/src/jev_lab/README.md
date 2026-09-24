# Reusable code

`client.py` provides a pinned-model TypeSafe Choice request, strict response validation, a request hash, and one bounded API call with no automatic retries. It has no trading or order capability. Add market adapters, feature calculation, policies, risk, accounting, and audit logging as the paper experiment requires them.

`binance_spot.py` reads and validates public, closed BTC/USDT klines. `paper.py` replays the frozen long-only baseline and two comparators with next-open fills, costs, and terminal liquidation. Both are read-only/paper components.
