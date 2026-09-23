import MetaTrader5 as mt5
import time

if not mt5.initialize():
    raise RuntimeError(mt5.last_error())

symbol = "XAUUSD"

mt5.symbol_select(symbol, True)

# Give terminal a moment to subscribe
time.sleep(3)

info = mt5.symbol_info(symbol)
tick = mt5.symbol_info_tick(symbol)

print("=== XAUUSD CONTRACT ===")
print("Visible:", info.visible)
print("Trade mode:", info.trade_mode)

print("Contract size:", info.trade_contract_size)
print("Minimum lot:", info.volume_min)
print("Lot step:", info.volume_step)

print("Tick size:", info.trade_tick_size)
print("Tick value:", info.trade_tick_value)

print()
print("=== CURRENT TICK ===")
print(tick)

# Use current tick if available,
# otherwise fallback to recent candle price.
if tick is not None and tick.ask > 0:
    price = tick.ask
else:
    rates = mt5.copy_rates_from_pos(
        symbol,
        mt5.TIMEFRAME_M1,
        0,
        2
    )

    price = rates[-1]["close"]

print()
print("Price used:", price)

margin = mt5.order_calc_margin(
    mt5.ORDER_TYPE_BUY,
    symbol,
    info.volume_min,
    price
)

print()
print("=== MINIMUM POSITION ===")
print("Volume:", info.volume_min)
print("Required margin:", margin)

# See what a $1 move in gold does
profit_1usd = mt5.order_calc_profit(
    mt5.ORDER_TYPE_BUY,
    symbol,
    info.volume_min,
    price,
    price + 1.0
)

print("Profit from +$1 gold move:", profit_1usd)

mt5.shutdown()