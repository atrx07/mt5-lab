# Algorithms

## Common execution model

Every live-paper version uses MT5 for price data but simulates execution locally.

For a BUY:

```text
entry = ask
exit  = bid
```

For a SELL:

```text
entry = bid
exit  = ask
```

This ensures the spread is paid rather than accidentally ignored.

Synthetic position size after V1:

```python
capital_usd = balance_inr / INR_PER_USD
notional_usd = capital_usd * LEVERAGE * EXPOSURE_FRACTION
ounces = notional_usd / price
synthetic_lots = ounces / 100.0
```

The broker minimum observed during testing was 0.01 lot, while the ₹500 research size was only around 0.0012 synthetic lots. These paper results therefore do not imply that the same account can execute the same size live.

---

## V1 — immediate breakout / momentum

### Entry

- recent breakout;
- 5 s momentum beyond a fixed threshold;
- acceptable spread.

### Exit

- momentum reversal;
- maximum holding time.

### Failure

Position sizing dominated everything. A fixed 1 oz position was absurd relative to ₹100.

---

## V2 — dynamically sized momentum breakout

Same basic signal family as V1, but exposure scales with account equity.

### Improvement

The account became survivable.

### Failure

The strategy fired too often and repeatedly paid a large spread relative to expected move size.

---

## V3 — confirmed multi-horizon breakout

### Entry

- 5 s momentum and 15 s momentum point in the same direction;
- 5 s momentum must exceed both:
  - a fixed minimum; and
  - a multiple of the current spread;
- price must break a recent range;
- setup persists for ~2 s before entry.

### Exit

- hard loss cap;
- peak-profit tracking;
- profit-lock after a threshold;
- reversal must persist for multiple samples;
- max holding time.

### Failure

Armed state was too fragile. A temporary spread excursion reset the setup.

---

## V3.1 — persistent armed breakout

V3.1 fixes the setup-state problem.

Once armed:

- the breakout level is frozen;
- temporary spread widening does not erase the signal;
- the setup may remain armed for a bounded number of seconds;
- direction must remain valid;
- actual entry still requires acceptable spread and renewed momentum confirmation.

### Failure pattern

The strategy still tends to enter *after* a fast move becomes obvious. On a violent instrument this often means paying the spread near the end of an impulse.

---

## V4 — pullback / resumption state machine

V4 changes the trading philosophy rather than simply tuning V3.1.

### State 0 — RESET

No directional impulse is active.

A new impulse is recognised only if multi-horizon momentum is strong enough and spread is acceptable.

### State 1 — IMPULSE

A directional move exists.

Do **not** enter immediately.

The bot waits for price to pull back against the direction while the slower momentum context remains intact.

### State 2 — PULLBACK

The bot has observed retracement from the impulse extreme.

Entry requires a resumption:

- price turns back with the original direction;
- short momentum re-accelerates;
- price is not excessively stretched;
- spread remains below the tighter ceiling.

### State 3 — IN TRADE

Deterministic risk management owns the position.

No model/API call is needed to exit.

### State 4 — LOCKOUT

After exit, the current impulse is considered consumed.

The bot waits for:

- cooldown; and
- a genuine momentum reset

before allowing another trade in the same direction.

This is the **one trade per impulse** rule.

---

## Why V4 may be better suited to XAUUSD

V3.x effectively says:

> the move is obvious, therefore enter.

V4 instead says:

> the move is established; now wait for the market to offer a less stretched entry, then require resumption.

That directly targets the two strongest failure modes observed in V3.1:

1. late entry into mature bursts;
2. repeated spread payment during choppy / hostile conditions.

---

## Future JEV integration

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
