import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from typing import Optional
from dataclasses import dataclass
from mplfinance.original_flavor import candlestick_ohlc
import logging
from concurrent.futures import ThreadPoolExecutor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class StockData:
    ticker: str
    data: pd.DataFrame

# ----------------------------- STOCK DATA FUNCTIONS -----------------------------

def fetch_stock_data(ticker: str, period: str = "1y") -> Optional[StockData]:
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period=period)
        if data.empty:
            logger.warning(f"No data available for {ticker}")
            return None
        return StockData(ticker, data)
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {str(e)}")
        return None

def detect_trend(stock_data: StockData) -> StockData:
    stock_data.data['Trend'] = np.where(stock_data.data['Close'] > stock_data.data['Close'].shift(1), 'Positive', 'Negative')
    return stock_data

def calculate_rsi(stock_data: StockData, window: int = 14) -> StockData:
    delta = stock_data.data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    stock_data.data['RSI'] = 100 - (100 / (1 + rs))
    return stock_data

def calculate_macd(stock_data: StockData, short_window: int = 12, long_window: int = 26, signal_window: int = 9) -> StockData:
    stock_data.data['EMA_short'] = stock_data.data['Close'].ewm(span=short_window, adjust=False).mean()
    stock_data.data['EMA_long'] = stock_data.data['Close'].ewm(span=long_window, adjust=False).mean()
    stock_data.data['MACD'] = stock_data.data['EMA_short'] - stock_data.data['EMA_long']
    stock_data.data['Signal Line'] = stock_data.data['MACD'].ewm(span=signal_window, adjust=False).mean()
    return stock_data

def calculate_bollinger_bands(stock_data: StockData, window: int = 20) -> StockData:
    stock_data.data['SMA'] = stock_data.data['Close'].rolling(window=window).mean()
    stock_data.data['Bollinger Upper'] = stock_data.data['SMA'] + (2 * stock_data.data['Close'].rolling(window=window).std())
    stock_data.data['Bollinger Lower'] = stock_data.data['SMA'] - (2 * stock_data.data['Close'].rolling(window=window).std())
    return stock_data

# ----------------------------- GRAPH PLOTTING FUNCTIONS -----------------------------

def plot_trend(stock_data: StockData):
    plt.figure(figsize=(14, 7))
    plt.plot(stock_data.data['Close'], label=f'{stock_data.ticker} Closing Price', color='blue')
    plt.fill_between(stock_data.data.index, stock_data.data['Close'], 
                     color=np.where(stock_data.data['Trend'] == 'Positive', 'green', 'red'), alpha=0.1)
    plt.title(f'{stock_data.ticker} Stock Price and Trend')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid()
    plt.show()

def plot_rsi(stock_data: StockData):
    plt.figure(figsize=(10, 5))
    plt.plot(stock_data.data['RSI'], label=f'{stock_data.ticker} RSI', color='purple')
    plt.axhline(70, color='red', linestyle='--', label='Overbought')
    plt.axhline(30, color='green', linestyle='--', label='Oversold')
    plt.title(f'{stock_data.ticker} Relative Strength Index (RSI)')
    plt.xlabel('Date')
    plt.ylabel('RSI')
    plt.legend()
    plt.grid()
    plt.show()

def plot_macd(stock_data: StockData):
    plt.figure(figsize=(10, 5))
    plt.plot(stock_data.data['MACD'], label='MACD', color='blue')
    plt.plot(stock_data.data['Signal Line'], label='Signal Line', color='red')
    plt.fill_between(stock_data.data.index, stock_data.data['MACD'] - stock_data.data['Signal Line'], 
                     color='gray', alpha=0.3, label='MACD - Signal')
    plt.title(f'{stock_data.ticker} Moving Average Convergence Divergence (MACD)')
    plt.xlabel('Date')
    plt.ylabel('MACD')
    plt.legend()
    plt.grid()
    plt.show()

def plot_bollinger_bands(stock_data: StockData):
    plt.figure(figsize=(10, 5))
    plt.plot(stock_data.data['Close'], label=f'{stock_data.ticker} Closing Price', color='blue')
    plt.plot(stock_data.data['Bollinger Upper'], label='Upper Band', linestyle='--', color='orange')
    plt.plot(stock_data.data['Bollinger Lower'], label='Lower Band', linestyle='--', color='orange')
    plt.fill_between(stock_data.data.index, stock_data.data['Bollinger Lower'], 
                     stock_data.data['Bollinger Upper'], color='gray', alpha=0.3)
    plt.title(f'{stock_data.ticker} Bollinger Bands')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid()
    plt.show()

def plot_candlestick(stock_data: StockData):
    ohlc = stock_data.data[['Open', 'High', 'Low', 'Close']].copy()
    ohlc['Date'] = mdates.date2num(stock_data.data.index)
    ohlc = ohlc[['Date', 'Open', 'High', 'Low', 'Close']]
    
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    candlestick_ohlc(ax, ohlc.values, width=0.6, colorup='green', colordown='red', alpha=0.8)
    
    plt.title(f'{stock_data.ticker} Candlestick Chart')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.grid()
    plt.show()

# ----------------------------- CLI INTERFACE -----------------------------

def select_ticker() -> str:
    return input("Enter the stock ticker symbol: ").upper()

def select_period() -> str:
    periods = {"1": "1mo", "2": "3mo", "3": "6mo", "4": "1y", "5": "2y", "6": "5y", "7": "10y", "8": "ytd", "9": "max"}
    print("\nSelect a time period:")
    for key, value in periods.items():
        print(f"{key}. {value}")
    choice = input("Enter your choice (1-9): ")
    return periods.get(choice, "1y")

def graph_menu():
    while True:
        print("\n--- Stock Graphing Menu ---")
        ticker = select_ticker()
        if not ticker:
            logger.warning("No valid ticker selected.")
            return

        period = select_period()
        stock_data = fetch_stock_data(ticker, period)
        if not stock_data:
            continue

        # Calculate different analyses concurrently
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(detect_trend, stock_data),
                executor.submit(calculate_rsi, stock_data),
                executor.submit(calculate_macd, stock_data),
                executor.submit(calculate_bollinger_bands, stock_data)
            ]
            for future in futures:
                stock_data = future.result()

        print("\n--- Display Options ---")
        print("1. Trend and Closing Price")
        print("2. RSI (Relative Strength Index)")
        print("3. MACD (Moving Average Convergence Divergence)")
        print("4. Bollinger Bands")
        print("5. Candlestick Chart")
        choice = input("Enter the type of display you want (1-5): ")

        plot_functions = {
            '1': plot_trend,
            '2': plot_rsi,
            '3': plot_macd,
            '4': plot_bollinger_bands,
            '5': plot_candlestick
        }

        if choice in plot_functions:
            plot_functions[choice](stock_data)
        else:
            logger.warning("Invalid choice. Please try again.")

        if input("Would you like to graph another stock? (y/n): ").lower() != 'y':
            break

# ----------------------------- MAIN MENU -----------------------------

def main_menu():
    while True:
        print("\n--- Main Menu ---")
        print("1. View Stock Quotes")
        print("2. Graph Stock Data")
        print("3. Log Out")
        choice = input("Enter your choice: ")
        try:
            if choice == '1':
                # Existing functionality for stock quotes can go here
                pass
            elif choice == '2':
                graph_menu()
            elif choice == '3':
                logger.info("Logging out...")
                break
            else:
                logger.warning("Invalid choice. Please try again.")
        except Exception as e:
            logger.error(f"An error occurred: {str(e)}")

# Entry point
if __name__ == "__main__":
    main_menu()
