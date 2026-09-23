# Common execution model

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
