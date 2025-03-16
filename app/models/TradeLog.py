from sqlalchemy import Column, Date, Float, Integer, String, schema
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TradeLog(Base):
    __tablename__ = 'trade_log'
    __table_args__ = {'schema': 'fyp'}

    report_date = Column(Date, primary_key=True)
    ticker = Column(String, primary_key=True)
    strategy = Column(String, primary_key=True)
    action = Column(String) 
    price = Column(Float(8))
    amount = Column(Float(8))
    note = Column(String)

    def __repr__(self):
        return f"<TradeLog(date={self.report_date}, ticker={self.ticker}, strategy={self.strategy})>"