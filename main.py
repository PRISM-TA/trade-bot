from app.db.session import create_db_session
from app.db.TradeLogUpload import upload_trade_logs_to_database
from app.strategies.LongOnlyStrategy import LongOnlyStrategy, LongOnlyStrategyParam
from app.strategies.BAHStrategy import BAHStrategy, BAHParam
from app.strategies.ShortOnlyStrategy import ShortOnlyStrategy, ShortOnlyStrategyParam
from app.strategies.RouletteStrategy import RouletteStrategy, RouletteStrategyParam, DecisionFactory
from app.pnl.PnLReporting import calculate_pnl
from app.datafeed.DataFeeder import DataFeeder

from dotenv import load_dotenv
import os

model = "CNNv0"
feature_set = "processed technical indicators (20 days)"

load_dotenv()
session = create_db_session(
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    port=os.getenv("DB_PORT")
)

feeder = DataFeeder(session)

params_target = ShortOnlyStrategyParam(
    sell_counter_threshold=3,
    stop_loss_percentage=-0.05,
    holding_period=20,
    initial_capital=10000
)
strategy_target = ShortOnlyStrategy(feeder, params_target)

# params_target = RouletteStrategyParam(
#     initial_capital=10000,
#     roulette_size=20,
#     decision_factory=DecisionFactory
# )
# strategy_target = RouletteStrategy(feeder, params_target)

# params_target = LongOnlyStrategyParam(
#     sell_counter_threshold=3,
#     stop_loss_percentage=-0.05,
#     holding_period=20,
#     initial_capital=10000
# )
# strategy_target = LongOnlyStrategy(feeder, params_target)

params_benchmark = BAHParam(
    initial_capital=10000
)
strategy_benchmark = BAHStrategy(feeder, params_benchmark)

for ticker in ["AAPL", "AXP", "BA", "CAT", "CSCO", "CVX", "DD", "DIS", "GE", "HD", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM", "MRK", "MSFT", "NKE", "PFE", "PG", "TRV", "UNH", "UTX", "VZ", "WMT", "XOM"]:
    pnl_stats = {}
    for strategy in [strategy_target, strategy_benchmark]:
        # Reset states
        strategy.reset()

        # Run strategy
        strategy.run(
            ticker=ticker,
            model=model,
            feature_set=feature_set
        )

        # Get results
        results = strategy.dump_trade_logs()

        # Calculate PnL
        pnl = calculate_pnl(10000, results)
        pnl_stats[strategy.strategy_name] = pnl
        
    result_status = "PASS" if pnl_stats[strategy_target.strategy_name] > pnl_stats[strategy_benchmark.strategy_name] else "FAIL"
    
    print(f"\033[{'92m' if result_status == 'PASS' else '91m'}[{result_status}]\033[0m {ticker:6} | BAH: {pnl_stats[strategy_benchmark.strategy_name]:12.2f} | TARGET: {pnl_stats[strategy_target.strategy_name]:12.2f}")
