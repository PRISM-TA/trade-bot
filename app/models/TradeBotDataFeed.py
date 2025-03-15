from sqlalchemy import Column, Integer, String, Date, Float
from dataclasses import dataclass
from datetime import date

@dataclass
class TradeBotDataFeed:
    report_date: date
    ticker: str
    model: str
    feature_set: str
    uptrend_prob: float
    side_prob: float
    downtrend_prob: float
    predicted_label: int
    open: float
    close: float

    def __repr__(self):
        return f"<TradeBotDataFeed(date={self.report_date}, ticker={self.ticker}, " \
               f"model={self.model}, feature_set={self.feature_set}, open={self.open}, close={self.close})>"