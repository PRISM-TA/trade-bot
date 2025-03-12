from db.session import create_db_session

from models.ClassifierResult import ClassifierResult
from models.MarketData import MarketData

from sqlalchemy import select
from sqlalchemy.orm import aliased
from dotenv import load_dotenv
import os

class condition:
    uptrend = 0
    sideway = 1
    downtrend = 2

ticker = "CVX"
model = "CNNv0"
feature_set = "processed technical indicators (20 days)"
start_date = "2007-01-01"

# Step 1 - Pull one year worth of data from the database
load_dotenv()
session = create_db_session(
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    port=os.getenv("DB_PORT")
)
with session() as db:
    # Create an alias for the subquery
    classifier_subq = (
        select(ClassifierResult)
        .where(
            (ClassifierResult.ticker == ticker) &
            (ClassifierResult.model == model) &
            (ClassifierResult.feature_set == feature_set)
        )
        .alias('classifier_subq')
    )

    # Perform the main query with a left join
    query = (
        select(MarketData, classifier_subq.c)
        .select_from(
            classifier_subq.join(
                MarketData,
                (classifier_subq.c.report_date == MarketData.report_date)
                & (classifier_subq.c.ticker == MarketData.ticker)
            )
        )
        .where(MarketData.report_date >= start_date)
    ).order_by(MarketData.report_date)

    query_result = db.execute(query).all()

# Step 2 - Initialize
capital = 10000
buy_spot = 0
sell_spot = 0
bought = False
day_counter = 0
non_buy_counter = 0

sell_counter_threshold = 3
stop_loss_percentage = -0.05  # Define the stop-loss threshold as a percentage (e.g., -5%)
percentage_changes = []

# Step 3 - Loop each day
for item in query_result:
    market_data = item[0]
    classifier_result = {
        'prediction': item[-2]
    }

    # If the classification result is up and currently not buying -> buy at current price
    if not bought and classifier_result['prediction'] == condition.uptrend:
        buy_spot = market_data.close
        bought = True
        day_counter = 0
        non_buy_counter = 0
        print(f"Bought {ticker} on {market_data.report_date} at {buy_spot}")
        continue

    # This result will be valid for 20 days
    if classifier_result['prediction'] == condition.uptrend:
        non_buy_counter = 0
        day_counter += 1
        if day_counter == 20:
            non_buy_counter = sell_counter_threshold - 1
    else:
        non_buy_counter += 1

    # Check for stop-loss trigger
    if bought:
        current_loss_percentage = (market_data.close - buy_spot) / buy_spot
        if current_loss_percentage <= stop_loss_percentage:
            sell_spot = market_data.close
            bought = False
            day_counter = 0
            non_buy_counter = 0
            print(f"Stop-loss triggered! Sold {ticker} on {market_data.report_date} at {sell_spot}, loss {(current_loss_percentage * 100):.2f}%")
            percentage_changes.append(current_loss_percentage)
            continue

    # Sell if non-buy counter threshold is reached (exit strategy without stop-loss trigger)
    if bought and non_buy_counter >= sell_counter_threshold:
        sell_spot = market_data.close
        bought = False
        day_counter = 0
        non_buy_counter = 0
        print(f"Sold {ticker} on {market_data.report_date} at {sell_spot}, gained {(sell_spot - buy_spot)/buy_spot * 100:.2f}%")
        percentage_changes.append((sell_spot - buy_spot) / buy_spot)
        continue

# Calculate final capital after applying all trades
for change in percentage_changes:
    capital *= (1 + change)

print(f"Final Capital: {capital}")
