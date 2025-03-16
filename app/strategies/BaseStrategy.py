from app.datafeed.DataFeeder import DataFeeder
from app.models.TradeLog import TradeLog

from datetime import date

class BaseStrategyParam:
    pass

class BaseStrategy:
    strategy_name: str
    trades: list[TradeLog]

    def _handle_buy(self, ticker: str, date: date, price: float, portion: float):
        self.trades.append(
            TradeLog(
                report_date=date,
                ticker=ticker,
                strategy=self.strategy_name,
                action='BUY',
                price=price,
                portion=portion
            )
        )
    
    def _handle_sell(self, ticker: str, date: date, price: float, portion: float, reason: str):
        self.trades.append(
            TradeLog(
                report_date=date,
                ticker=ticker,
                strategy=self.strategy_name,
                action='SELL',
                price=price,
                portion=portion,
                note=reason
            )
        )
    
    def __init__(self, datafeeder: DataFeeder, param: BaseStrategyParam):
        self.datafeeder = datafeeder
        self.param = param

    def run(self):
        pass
        
    def dump_trade_logs(self)->list[TradeLog]:
        pass