from app.models.TradeLog import TradeLog

def calculate_pnl(initial_capital: float, trade_logs: list[TradeLog]) -> float:
    current_capital = initial_capital
    holdings = {}  # Dictionary to track holdings per ticker

    for trade in trade_logs:
        if trade.action == 'BUY':
            buy_amount = current_capital * (trade.portion / 100)
            shares_bought = buy_amount / trade.price
            current_capital -= buy_amount

            if trade.ticker in holdings:
                holdings[trade.ticker] += shares_bought
            else:
                holdings[trade.ticker] = shares_bought

        elif trade.action == 'SELL':
            if trade.ticker in holdings and holdings[trade.ticker] > 0:
                sell_amount = holdings[trade.ticker] * (trade.portion / 100) * trade.price
                holdings[trade.ticker] -= holdings[trade.ticker] * (trade.portion / 100)
                current_capital += sell_amount
            else:
                print(f"No sufficient holdings found for {trade.ticker} to sell")

        else:
            print(f"Unexpected action type: {trade.action}")
    
    pnl = current_capital - initial_capital
    return pnl
       