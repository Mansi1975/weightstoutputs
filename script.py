import pandas as pd
from typing import Tuple

class Strategy():
   def process_data(self, data) -> pd.DataFrame:
      return data
   def get_signals(self, tradingState: dict) -> Tuple[list, str]:

      tickers = tradingState['positions'].index
      
      # Create equal weight signals for all stocks
      num_tickers = len(tickers)
      signal = pd.Series(-1 / num_tickers, index=tickers)  # Equal weight for each stock
      
      # Trader data can be updated or left as an empty string
      traderData = "Equal weight signals generated"
      
      return signal, traderData