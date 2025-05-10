Variables

import time
from datetime import datetime, timedelta
from alpaca.data.historical import CryptoHistoricalDataClient
from alpaca.data.requests import CryptoBarsRequest
from alpaca.data.timeframe import TimeFrame
import alpaca_trade_api as tradeapi

# Directly written API keys (NOT recommended for production or public repos)
API_KEY = "PKEXQW93W9K2IPE8S0UX"
SECRET_KEY = "go28YfYeGif9v8FuIvv9qSyCKxyvzjvG6aHIkRid"

# Alpaca clients
data_client = CryptoHistoricalDataClient(API_KEY, SECRET_KEY)
trade_client = tradeapi.REST(API_KEY, SECRET_KEY, base_url='https://paper-api.alpaca.markets')

# Config
coin_pairs = [
    "BTC/USD", "ETH/USD", "SOL/USD", "AVAX/USD", "MATIC/USD",
    "LTC/USD", "BCH/USD", "UNI/USD", "AAVE/USD", "SUSHI/USD",
    "LINK/USD", "DOGE/USD", "SHIB/USD", "ATOM/USD", "ALGO/USD",
    "DOT/USD", "APE/USD"
]
VOLATILITY_THRESHOLD = 0.3
PROFIT_TARGET = 0.03
STOP_LOSS_THRESHOLD = -0.10
entry_prices = {}

def get_dynamic_notional():
    account = trade_client.get_account()
    total_cash = float(account.cash)
    return total_cash * 0.01

def scan_and_trade():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scanning for trades...")
    end = datetime.now()
    start = end - timedelta(minutes=5)

    for symbol in coin_pairs:
        try:
            request = CryptoBarsRequest(
                symbol_or_symbols=symbol,
                timeframe=TimeFrame.Minute,
                start=start,
                end=end
            )
            bars = data_client.get_crypto_bars(request).df

            if symbol in bars.index.get_level_values(0):
                df = bars.loc[symbol]
                df['pct_change'] = df['close'].pct_change().fillna(0) * 100
                max_change = df['pct_change'].abs().max()
                latest_price = df['close'].iloc[-1]
                trade_symbol = symbol.replace("/", "")

                if trade_symbol in entry_prices:
                    bought_price = entry_prices[trade_symbol]
                    gain = (latest_price - bought_price) / bought_price

                    if gain >= PROFIT_TARGET:
                        print(f"{symbol}: Target reached (+{gain*100:.2f}%) - SELLING")
                        position = trade_client.get_position(trade_symbol)
                        trade_client.submit_order(
                            symbol=trade_symbol,
                            qty=position.qty,
                            side='sell',
                            type='market',
                            time_in_force='gtc'
                        )
                        del entry_prices[trade_symbol]
                        continue

                    elif gain <= STOP_LOSS_THRESHOLD:
                        print(f"{symbol}: Stop-loss triggered ({gain*100:.2f}%) - SELLING")
                        position = trade_client.get_position(trade_symbol)
                        trade_client.submit_order(
                            symbol=trade_symbol,
                            qty=position.qty,
                            side='sell',
                            type='market',
                            time_in_force='gtc'
                        )
                        del entry_prices[trade_symbol]
                        continue

                    else:
                        print(f"{symbol}: Holding ({gain*100:.2f}%)")

                elif max_change >= VOLATILITY_THRESHOLD and trade_symbol not in entry_prices:
                    print(f"{symbol} volatile ({max_change:.2f}%) - BUYING")
                    notional = get_dynamic_notional()
                    trade_client.submit_order(
                        symbol=trade_symbol,
                        notional=notional,
                        side='buy',
                        type='market',
                        time_in_force='gtc'
                    )
                    entry_prices[trade_symbol] = latest_price
                else:
                    print(f"{symbol} not volatile or already in position ({max_change:.2f}%)")
            else:
                print(f"No data for {symbol}")

        except Exception as e:
            print(f"Error with {symbol}: {e}")

while True:
    scan_and_trade()
    time.sleep(300)
