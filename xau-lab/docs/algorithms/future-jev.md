# Future JEV integration

The planned JEV architecture should keep model inference outside the emergency risk path.

```text
MT5 ticks
  ↓
local feature/state engine
  ↓
candidate setup
  ↓
JEV: BUY / SELL / HOLD + confidence
  ↓
local deterministic veto / risk engine
  ↓
paper execution
```

Once a position exists, hard stop, trailing/profit protection, connection-failure handling and any future broker-native SL/TP should remain deterministic and local/server-side rather than waiting on a remote model response.
