from app.db.session import create_db_session
from app.db.TradeLogUpload import upload_trade_logs_to_database
from app.strategies.LongOnlyStrategy import LongOnlyStrategy, LongOnlyStrategyParam
from app.strategies.BAHStrategy import BAHStrategy, BAHParam
from app.datafeed.DataFeeder import DataFeeder

from dotenv import load_dotenv
import os


ticker = "CVX"
model = "CNNv0"
feature_set = "processed technical indicators (20 days)"

# Step 1 - Pull one year worth of data from the database
load_dotenv()
session = create_db_session(
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    port=os.getenv("DB_PORT")
)

feeder = DataFeeder(session)
query_result = feeder.pullData(ticker, model, feature_set)
print(repr(query_result))

# Initialize strategy
# params = LongOnlyStrategyParam(
#     sell_counter_threshold=3,
#     stop_loss_percentage=-0.05,
#     holding_period=20
# )
# strategy = LongOnlyStrategy(feeder, params)

params = BAHParam()
strategy = BAHStrategy(feeder, params)

# Run strategy
strategy.run(
    ticker="CVX",
    model="CNNv0",
    feature_set="processed technical indicators (20 days)"
)

# Get results
results = strategy.dump_trade_logs()

# Print individual trades
for trade in results:
    if trade.action == 'BUY':
        print(f"Bought on {trade.report_date} at ${trade.price:.2f}")
    else:
        print(f"Sold on {trade.report_date} at ${trade.price:.2f} - {trade.note}")

# Upload trade logs
# upload_trade_logs_to_database(session, results)