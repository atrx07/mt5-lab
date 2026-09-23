# Experiment log

## 2026-09-23 — contract probe

The MT5 symbol probe established the practical constraints that shaped every later experiment.

Observed around XAUUSD ~4315:

- contract size: 100 oz per lot;
- broker minimum: 0.01 lot = 1 oz;
- at 1:100 leverage, minimum margin was roughly USD 43;
- a USD 1 move in gold on 0.01 lot changes P&L by roughly USD 1;
- observed spread during the session varied from roughly USD 0.2 into the USD 0.5+ range.

This immediately showed that the intended ₹100 or ₹500 challenge sizes could not place the broker's minimum live XAUUSD contract. All subsequent small-account tests therefore used **synthetic fractional exposure** for research only.

---

## V1 — `paper_challenge.py`

### Goal

Try ₹100 → ₹150 using live XAUUSD prices.

### Design

- fixed synthetic exposure: 1.00 oz;
- sample interval: ~0.5 s;
- warmup: 30 s;
- spread ceiling: USD 0.35;
- 5 s momentum threshold: USD 0.30;
- breakout buffer: USD 0.05;
- cooldown: 15 s;
- max hold: 120 s.

### Recorded run

- SELL #1 entry bid: 4314.45
- spread: 0.22
- immediate spread handicap: about -₹21.05
- first trade exit: -₹72.73
- balance after trade: ₹27.27
- SELL #2 spread: 0.30
- immediate spread handicap: about -₹28.71
- final balance: **-₹13.89**
- elapsed from start to ruin: roughly **42 seconds**

### Finding

The dominant failure was not signal quality; it was sizing. One ounce against ₹100 was effectively thousands of times exposure relative to capital. Ordinary sub-dollar gold movement and spread were enough to destroy the account.

---

## V2 — `paper_challenge_v2.py`

### Change from V1

Replace fixed 1 oz sizing with dynamic fractional exposure:

```text
capital_usd = balance_inr / INR_PER_USD
notional_usd = capital_usd * leverage
ounces = notional_usd / XAUUSD_price
```

At ₹500, 100x synthetic leverage, and gold around 4300, exposure was roughly 0.12 oz (~0.0012 synthetic lots).

### Recorded run

- starting balance: ₹500
- final balance: **₹475.48**
- trades: 6
- net: **-₹24.52 (-4.9%)**
- only one material winner: about +₹15.16
- total entry spread handicap was about ₹21.34

### Finding

Dynamic sizing stopped the instant account explosion, but the strategy over-traded. Transaction friction was of the same order as the whole drawdown.

---

## V3 — `paper_challenge_v3.py`

### Main changes

- 5 s and 15 s momentum must agree;
- 2 s breakout confirmation;
- max loss per trade reduced to ₹25;
- profit lock activates at ₹8;
- 20 s cooldown;
- reversal requires persistence across multiple samples.

### Exact recorded CSV result

The original trade log is committed at `results/paper_trades_v3.csv`.

Summary:

| Trade | Side | P&L |
| --- | --- | ---: |
| 1 | BUY | -₹0.58 |
| 2 | BUY | -₹9.04 |
| 3 | SELL | -₹7.85 |

Final balance: **₹482.53**.

### Finding

V3 became much more selective, but the confirmation logic was too brittle: one temporary spread widening could completely erase an armed signal. The system repeatedly looked ready to enter, then forgot the setup.

---

## V3.1 — `paper_challenge_v3_1.py`

### Main changes

- armed signals survive temporary spread widening;
- max armed lifetime: 6 s;
- breakout level is frozen at arm time;
- setup is cancelled only when direction genuinely invalidates;
- spread must be acceptable at actual entry;
- same hard-stop / reversal / profit-lock framework.

### Exact recorded CSV result

The original trade log is committed at `results/paper_trades_v3_1.csv`.

Summary from the 18 completed trades:

- start: ₹500
- end: **₹463.46**
- net: **-₹36.54 (-7.31%)**
- winners: 5
- losers: 13
- one strong early winner: +₹13.79
- another strong winner: +₹15.75
- the first 14 trades left the account at **₹499.91**
- the final four trades were:
  - -₹5.80
  - -₹14.44
  - -₹6.45
  - -₹9.77

Those four trades account for almost the entire final drawdown.

### Spread split observed in that run

This is descriptive of one run, not a universal law:

| Entry spread | Trades | Aggregate P&L |
| --- | ---: | ---: |
| <= USD 0.30 | 11 | about -₹0.43 |
| > USD 0.30 | 7 | about -₹36.11 |

The result strongly suggested that a USD 0.35 entry ceiling was too permissive for this scalp horizon.

### Other observed failure modes

1. **Late momentum chasing** — confirmation can happen after the best part of the impulse is already gone.
2. **Give-back** — several trades reached small positive P&L and later closed near flat or negative because the ₹8 profit-lock trigger was too high for the typical move size.
3. **Regime persistence** — the bot kept trading after conditions became hostile.
4. **Spread sensitivity** — a few tenths of a dollar are enormous relative to the expected edge of a 5–30 second trade.

---

## Offline algorithm comparison — exploratory

Using the short broker quote clips captured during the live experiments, several strategy families were compared in fast replay. These exploratory numbers are retained as research notes, not as proof of out-of-sample profitability.

The strongest recurring idea was not raw momentum chasing, but:

**established direction → pullback → directional resumption**

A second useful finding was to enforce **one trade per impulse**, so the bot cannot repeatedly re-enter the same move after a win or loss.

The successor became the V4 research candidate.

---

## V4 research candidate

### Design direction

- maximum entry spread: USD 0.28;
- wait for a directional impulse;
- wait for a pullback instead of buying/selling the most stretched point;
- enter only after directional resumption;
- refuse a new trade in the same impulse until the market resets;
- hard stop around ₹8 on a ₹500 synthetic account;
- profit protection begins around ₹4;
- retain roughly 65% of peak paper profit once lock activates;
- ~45 s cooldown;
- ~60 s max hold;
- local deterministic exits remain authoritative.

The implementation is in `scripts/paper_challenge_v4.py`.

### What V4 is *not*

It is not declared profitable, production-ready, or suitable for real money. The next meaningful validation step is multi-day broker tick replay with walk-forward / untouched holdout windows.
