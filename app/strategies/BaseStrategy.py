from app.datafeed.DataFeeder import DataFeeder

class BaseStrategyParam:
    pass

class BaseStrategy:
    def __init__(self, datafeeder: DataFeeder, param: BaseStrategyParam):
        self.datafeeder = datafeeder
        self.param = param

    def run(self):
        pass
        
    def dump_trade_log(self):
        pass