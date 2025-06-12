import pandas as pd

# Load files
positions = pd.read_csv('positions.csv', index_col=0, parse_dates=True)
prices = pd.read_csv('multi_level_ohlcv.csv', header=[0, 1], index_col=0, parse_dates=True)

# Extract close prices
close_prices = prices.xs('close', level=1, axis=1)

# Align prices to positions
close_prices = close_prices.loc[positions.index, positions.columns]

# Position value = shares × price
position_value = positions * close_prices

# Total portfolio value
portfolio_value = position_value.sum(axis=1)

# Avoid division by zero (set 1 to avoid NaN; will fill weights with 0 later)
portfolio_value_safe = portfolio_value.replace(0, 1)

# Calculate weights
weights = position_value.div(portfolio_value_safe, axis=0)

# Wherever portfolio value was 0, set entire row to 0
weights[portfolio_value == 0] = 0

# Save weights
weights.index = weights.index.strftime('%Y-%m-%d %H:%M')
weights.to_csv('weights.csv')


print("✅ weights.csv saved. All rows retained with 0s where needed.")
