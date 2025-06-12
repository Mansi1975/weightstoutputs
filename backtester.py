import pandas as pd
import vectorbt as vbt
import tqdm
from script import Strategy

class Backtester:
    def __init__(self, data: pd.DataFrame, initial_value: float):
        self.data = data
        self.portfolio_value = initial_value
        self.cash = initial_value
        self.investment = 0.0
        self.current_index = 1
        tickers = data.columns.get_level_values(0).unique()
        self.positions = pd.Series(0, index=tickers)
        self.all_positions = pd.DataFrame(columns=tickers)
        self.weights = pd.DataFrame(columns=tickers)
        self.tradingState = {}

    def calculate_positions(self, signal: pd.Series, value, open=True) -> pd.Series:
        if not isinstance(signal, pd.Series):
            raise TypeError(f'For timestamp {self.data.index[self.current_index]}, signal must be a pandas Series, got {type(signal)}')
        if abs(signal).sum() - 1 > 1e-6:
            raise ValueError(f'For timestamp {self.data.index[self.current_index]} the sum of the abs(signals) must not be greater than 1, got {abs(signal).sum()}')
        index = self.current_index
        prices = self.data.xs('open',level=1,axis=1).iloc[index] if open else self.data.xs('close',level=1,axis=1).iloc[index]
        new_positions = (signal * value // prices).astype(int)
        new_positions += (new_positions < 0).astype(int) 
        return new_positions
    
    def update_investment(self, positions: pd.Series, new_day=False) -> float:
        index = self.current_index
        price1 = self.data.xs('close',level=1,axis=1).iloc[index-1] if new_day else self.data.xs('open',level=1,axis=1).iloc[index]
        price2 = self.data.xs('open',level=1,axis=1).iloc[index] if new_day else self.data.xs('close',level=1,axis=1).iloc[index]
        return (positions * (price2 - price1)).sum() + self.investment
    
    def calculate_cash(self, positions: pd.Series, open=True) -> float:
        index = self.current_index
        price = self.data.xs('open',level=1,axis=1).iloc[index] if open else self.data.xs('close',level=1,axis=1).iloc[index]
        return self.portfolio_value - (abs(positions) * price).sum()
    
    def run(self):
        processed_data = Strategy().process_data(self.data)
        self.all_positions.loc[self.data.index[0]] = self.positions

        # Compute weights
        price = self.data.xs('close', level=1, axis=1).iloc[self.current_index]
        position_value = self.positions * price
        weights = position_value / self.portfolio_value
        self.weights.loc[self.data.index[self.current_index]] = weights


        traderData = ""
        for i in tqdm.tqdm(range(1, len(self.data))):
            self.tradingState = {
                'processed_data': processed_data[:i],
                'investment': self.investment,
                'cash': self.cash,
                'current_timestamp': self.data.index[self.current_index],
                'traderData': traderData,
                'positions': self.positions,
            }
            signal, traderData = Strategy().get_signals(self.tradingState)
            signal.to_csv('signal.csv')
            print(traderData)
            if signal is None:
                raise ValueError(f'For timestamp {self.data.index[self.current_index]}, signal is None')
            self.investment = self.update_investment(self.positions, new_day=True) 
            self.portfolio_value = self.investment + self.cash
            self.positions = self.calculate_positions(signal, self.portfolio_value)
            self.cash = self.calculate_cash(self.positions)
            self.investment = self.portfolio_value - self.cash
            self.investment = self.update_investment(self.positions, new_day=False)
            self.portfolio_value = self.investment + self.cash
            self.current_index += 1
            self.all_positions.loc[self.data.index[i]] = self.positions
            
    def vectorbt_run(self):
        open_prices = self.data.xs('open', level=1, axis=1).loc[self.all_positions.index, self.all_positions.columns]
        close_prices = self.data.xs('close', level=1, axis=1).loc[self.all_positions.index, self.all_positions.columns]

        # Create order size = position change (diff)
        order_size = self.all_positions.diff().fillna(0).astype(int)
        order_size = order_size.mask(order_size == 0)
        order_size.to_csv('order_size.csv')

        # Execute trades at open price, value portfolio at close
        portfolio = vbt.Portfolio.from_orders(
            close=close_prices,            # value tracked using close
            size=order_size,               # actual number of shares traded
            price=open_prices,             # trades executed at open
            init_cash=initial_value,           
            freq='1D',
            direction=2,
            cash_sharing=True,   
        )
        print(portfolio.assets())
        trade_log = portfolio.trades.records_readable
        trade_log.to_csv('trade_log.csv')


if __name__ == "__main__":
    # Example usage
    data = pd.read_csv('multi_level_ohlcv.csv', index_col=0, header=[0,1], parse_dates=True)
    
    first_5_tickers = data.columns.get_level_values(0).unique()[0:20]
    data = data.loc[:, data.columns.get_level_values(0).isin(first_5_tickers)]

    data = data.tail(5)
    initial_value = 500000.0  # Initial portfolio value
    backtester = Backtester(data, initial_value)
    backtester.run()
    
    print("Final Portfolio Value:", backtester.portfolio_value)
    print("Positions:\n", backtester.all_positions)
    backtester.all_positions.to_csv('positions.csv')
    backtester.vectorbt_run()
    
    backtester.weights.to_csv('weights.csv')
     
    