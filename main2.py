from db.session import create_db_session
from models.ClassifierResult import ClassifierResult
from models.MarketData import MarketData

from sqlalchemy import select
from dotenv import load_dotenv
import os

class Condition:
    uptrend = 0
    sideway = 1
    downtrend = 2

ticker = "CVX"
model = "CNNv0"
feature_set = "processed technical indicators (20 days)"
start_date = "2007-01-01"

initial_capital = 10000.0
risk_per_trade = 0.02   # fraction of current capital to risk per trade
sell_counter_threshold = 3

confidence_threshold_buy = 0.6   # must have at least 60% confidence in "uptrend" to buy
confidence_threshold_sell = 0.6  # can force an exit if "downtrend" or "sideway" is over 60% confidence

init_stop_loss_pct = -0.05  # -5% initial stop-loss
trailing_stop_gap = 0.05    # 5% behind the highest reached price since entry

load_dotenv()

session = create_db_session(
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    port=os.getenv("DB_PORT")
)

with session() as db:
    # Fetch classifier data.
    # IMPORTANT: Ensure your ClassifierResult has "prediction" AND a "confidence" (or similar) field.
    # Adjust if your schema differs.
    classifier_subq = (
    select(ClassifierResult)
    .where(
    (ClassifierResult.ticker == ticker) &
    (ClassifierResult.model == model) &
    (ClassifierResult.feature_set == feature_set)
    )
    .alias('classifier_subq')
    )

    # Join classifier data with MarketData
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
        .order_by(MarketData.report_date)
    )

    query_result = db.execute(query).all()

price_history = []
predictions = []
confidences = []
for row in query_result:
    market_data = row[0]
    # Adjust indices according to the actual columns in your table
    pred_value = row[-2]  # ClassifierResult.prediction
    conf_value = row[-1]  # ClassifierResult.confidence
    price_history.append((market_data.report_date, market_data.close))
    predictions.append(pred_value)
    confidences.append(conf_value)

    if price_history:
        bh_initial_price = price_history[0][1]
        bh_final_price = price_history[-1][1]
        bh_return_factor = bh_final_price / bh_initial_price
        bh_final_capital = initial_capital * bh_return_factor
    else:
        bh_final_capital = initial_capital  # Edge case: no data


capital = initial_capital
bought = False
units_held = 0.0        # how many shares of the ticker we hold
entry_price = 0.0       # price at which we entered
highest_price_since_buy = 0.0
current_stop_loss_level = 0.0

day_counter = 0
non_buy_counter = 0

trade_returns = []

for i, (date, price) in enumerate(price_history):
    pred = predictions[i]
    conf = confidences[i]
    if not bought:
        # 1) Attempt to buy if the classifier signals uptrend + meets confidence threshold
        if (pred == Condition.uptrend) and (conf >= confidence_threshold_buy):
            # Calculate position size based on risk_per_trade
            # We risk "risk_per_trade * capital" if the trade goes to the stop loss
            # e.g., if capital=10000 and risk_per_trade=2%, risk_amount=200
            # If our stop-loss is 5% below entry, then we can buy risk_amount / (price * 0.05) shares
            risk_amount = capital * risk_per_trade
            # The planned stop (init_stop_loss_pct) means we plan for price * (1 + init_stop_loss_pct)
            # e.g., if init_stop_loss_pct = -5%, stop-loss is price * 0.95
            # We'll keep it simple here:
            shares_to_buy = risk_amount / (price * abs(init_stop_loss_pct))  
            # Make sure to not exceed all capital
            cost = shares_to_buy * price
            if cost > capital:
                shares_to_buy = capital / price
                cost = shares_to_buy * price

            # Enter position
            bought = True
            units_held = shares_to_buy
            entry_price = price
            highest_price_since_buy = price
            day_counter = 0
            non_buy_counter = 0

            # Set initial stop-loss
            current_stop_loss_level = entry_price * (1.0 + init_stop_loss_pct)

            print(f"Bought on {date} @ {entry_price:.2f}, shares={units_held:.4f}, cost={cost:.2f}\n"
                f"Initial stop-loss set at {current_stop_loss_level:.2f}")
        else:
            # Not a buying condition, just skip
            pass

    else:
        # If we have a position open:
        # Update highest price + trailing stop if the price has risen
        if price > highest_price_since_buy:
            highest_price_since_buy = price
            # Update trailing stop (5% behind the highest price)
            current_stop_loss_level = highest_price_since_buy * (1.0 - trailing_stop_gap)
        
        # Calculate the current trade PNL percentage
        pnl_percentage = (price - entry_price) / entry_price
        
        # 2) Check if we hit trailing or initial stop-loss
        if price <= current_stop_loss_level:
            # Sell due to stop-loss
            proceeds = units_held * price
            trade_return = proceeds / (units_held * entry_price) - 1.0
            trade_returns.append(trade_return)

            # Update capital
            capital += proceeds
            bought = False
            units_held = 0.0
            print(f"[Stop-Loss or Trailing-Loss] Sold on {date} @ {price:.2f} | Trade Return = {trade_return*100:.2f}%")
            continue

        # 3) If classifier says uptrend, positive reinforcement
        if pred == Condition.uptrend and conf >= confidence_threshold_buy:
            day_counter += 1
            non_buy_counter = 0
            # Optionally partial exit or re-balance after a certain number of days
            # if day_counter >= 20: { your logic here }
        else:
            non_buy_counter += 1

            # If the classifier is strongly indicating sideway/downtrend (above threshold), exit early
            if conf >= confidence_threshold_sell:
                # Sell
                proceeds = units_held * price
                trade_return = proceeds / (units_held * entry_price) - 1.0
                trade_returns.append(trade_return)

                capital += proceeds
                bought = False
                units_held = 0.0
                day_counter = 0
                non_buy_counter = 0
                print(f"[Confidence-based Exit] Sold on {date} @ {price:.2f} | Trade Return = {trade_return*100:.2f}%")
                continue

            # 4) If reached threshold of consecutive “non-up” days, exit
            if non_buy_counter >= sell_counter_threshold:
                proceeds = units_held * price
                trade_return = proceeds / (units_held * entry_price) - 1.0
                trade_returns.append(trade_return)

                capital += proceeds
                bought = False
                units_held = 0.0
                day_counter = 0
                non_buy_counter = 0
                print(f"[Sell-Counter Exit] Sold on {date} @ {price:.2f} | Trade Return = {trade_return*100:.2f}%")
                continue

if bought and units_held > 0:
    last_date, last_price = price_history[-1]
    proceeds = units_held * last_price
    trade_return = proceeds / (units_held * entry_price) - 1.0
    trade_returns.append(trade_return)
    capital += proceeds
    print(f"[Final Exit] Sold on {last_date} @ {last_price:.2f} | Trade Return = {trade_return*100:.2f}%")


final_capital = capital
print("--------------------------------------------------")
print(f"Strategy Final Capital:    {final_capital:.2f}")
print(f"Buy-and-Hold Final Capital {bh_final_capital:.2f}")

if final_capital > bh_final_capital:
    print("Classifier-based strategy outperformed buy-and-hold.")
else:
    print("Buy-and-hold outperformed (or matched) the classifier-based strategy.")