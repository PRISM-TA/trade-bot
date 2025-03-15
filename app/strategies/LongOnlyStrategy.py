"""
Long-Only Strategy Description

Overview:
This is a trend-following strategy that takes long-only positions based on machine learning predictions of market conditions. The strategy uses a classifier model that predicts whether the market is in an uptrend, sideways, or downtrend state.

Entry Conditions:
- Enter long positions only when the classifier predicts an uptrend
- No short positions are taken (hence "Long-Only")
- New positions are only taken when not currently holding a position

Exit Conditions:
The strategy exits positions under three scenarios:
1. Stop Loss: Exit if the position loses more than the specified stop loss percentage (default -5%)
2. Counter Threshold: Exit if the classifier shows non-uptrend predictions for a consecutive number of days (default 3 days)
3. Holding Period: The uptrend prediction validity is limited to a specified number of days (default 20 days)

Parameters:
- initial_capital: Starting capital for the strategy (default $10,000)
- sell_counter_threshold: Number of consecutive non-uptrend days before forced exit (default 3 days)
- stop_loss_percentage: Maximum allowed loss before position is closed (default -5%)
- holding_period: Maximum number of days to hold based on a single uptrend prediction (default 20 days)

Trade Management:
- Each trade is recorded with entry/exit dates, prices, and reasons for exit
- Position sizing is fixed (100% of capital)
- Returns are compounded across trades
- Performance is tracked through trade records and capital changes

Risk Management:
- Stop loss orders to limit downside risk
- No leverage used
- Single position at a time
- Automatic exit on sustained trend reversal signals
"""
from app.models.MarketCondition import MarketCondition

from app.strategies.BaseStrategy import BaseStrategy, BaseStrategyParam
from app.datafeed.DataFeeder import DataFeeder

from dataclasses import dataclass
from typing import List, Dict
from datetime import date

@dataclass
class TradeRecord:
    date: date
    action: str  # 'BUY' or 'SELL'
    price: float
    percentage_change: float = None
    reason: str = None

class LongOnlyStrategyParam(BaseStrategyParam):
    def __init__(
        self,
        initial_capital: float = 10000,
        sell_counter_threshold: int = 3,
        stop_loss_percentage: float = -0.05,
        holding_period: int = 20
    ):
        self.initial_capital = initial_capital
        self.sell_counter_threshold = sell_counter_threshold
        self.stop_loss_percentage = stop_loss_percentage
        self.holding_period = holding_period

class LongOnlyStrategy(BaseStrategy):
    def __init__(self, datafeeder: DataFeeder, param: LongOnlyStrategyParam):
        super().__init__(datafeeder, param)
        self.capital = param.initial_capital
        self.trades: List[TradeRecord] = []
        self.percentage_changes: List[float] = []
        
        # Trading state
        self.buy_spot = 0
        self.sell_spot = 0
        self.bought = False
        self.day_counter = 0
        self.non_buy_counter = 0

    def _handle_buy(self, date: date, price: float):
        self.buy_spot = price
        self.bought = True
        self.day_counter = 0
        self.non_buy_counter = 0
        self.trades.append(
            TradeRecord(
                date=date,
                action='BUY',
                price=price
            )
        )

    def _handle_sell(self, date: date, price: float, reason: str):
        self.sell_spot = price
        self.bought = False
        self.day_counter = 0
        self.non_buy_counter = 0
        
        percentage_change = (price - self.buy_spot) / self.buy_spot
        self.percentage_changes.append(percentage_change)
        
        self.trades.append(
            TradeRecord(
                date=date,
                action='SELL',
                price=price,
                percentage_change=percentage_change,
                reason=reason
            )
        )

    def run(self, ticker: str, model: str, feature_set: str):
        datafeed = self.datafeeder.pullData(ticker=ticker, classifier_model=model, feature_set=feature_set)

        for daily_data in datafeed:
            # Buy MarketCondition
            if not self.bought and daily_data.predicted_label == MarketCondition.uptrend:
                self._handle_buy(daily_data.report_date, daily_data.close)
                continue

            # Update counters
            if daily_data.predicted_label == MarketCondition.uptrend:
                self.non_buy_counter = 0
                self.day_counter += 1
                if self.day_counter == self.param.holding_period:
                    self.non_buy_counter = self.param.sell_counter_threshold - 1
            else:
                self.non_buy_counter += 1

            # Check stop loss
            if self.bought:
                current_loss_percentage = (daily_data.close - self.buy_spot) / self.buy_spot
                if current_loss_percentage <= self.param.stop_loss_percentage:
                    self._handle_sell(
                        daily_data.report_date, 
                        daily_data.close,
                        f"Stop loss triggered at {current_loss_percentage:.2%}"
                    )
                    continue

            # Check sell counter threshold
            if self.bought and self.non_buy_counter >= self.param.sell_counter_threshold:
                self._handle_sell(
                    daily_data.report_date,
                    daily_data.close,
                    "Sell counter threshold reached"
                )
                continue

        # Calculate final capital
        self.capital = self.param.initial_capital
        for change in self.percentage_changes:
            self.capital *= (1 + change)

    def dump_trade_log(self) -> Dict:
        return {
            "initial_capital": self.param.initial_capital,
            "final_capital": self.capital,
            "total_return": (self.capital - self.param.initial_capital) / self.param.initial_capital,
            "number_of_trades": len(self.trades),
            "trades": self.trades
        }