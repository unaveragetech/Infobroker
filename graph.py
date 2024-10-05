import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from typing import Optional, List
from dataclasses import dataclass
from mplfinance.original_flavor import candlestick_ohlc
import logging
from concurrent.futures import ThreadPoolExecutor
import os
import json
from datetime import datetime
import plotly.graph_objs as go
import plotly.express as px

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ----------------------------- CACHING -----------------------------
CACHE_FILE = "stock_cache.json"
CACHE_EXPIRY_DAYS = 1  # Cache expires after 1 day

@dataclass
class StockData:
    ticker: str
    data: pd.DataFrame

# Load cache from file
def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as file:
            return json.load(file)
    return {}

# Save cache to file
def save_cache(cache: dict):
    with open(CACHE_FILE, 'w') as file:
        json.dump(cache, file)

# Check if cached data is expired
def is_cache_expired(cached_time: str) -> bool:
    cached_time = datetime.strptime(cached_time, '%Y-%m-%d %H:%M:%S')
    return (datetime.now() - cached_time).days > CACHE_EXPIRY_DAYS

# ----------------------------- STOCK DATA FUNCTIONS -----------------------------

# Fetch stock data with caching support
def fetch_stock_data(ticker: str, period: str = "1y") -> Optional[StockData]:
    cache = load_cache()
    if ticker in cache and not is_cache_expired(cache[ticker]['last_updated']):
        logger.info(f"Using cached data for {ticker}")
        return StockData(ticker, pd.DataFrame(cache[ticker]['data']))
    
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period=period)
        if data.empty:
            logger.warning(f"No data available for {ticker}")
            return None
        cache[ticker] = {
            'data': data.to_dict(),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        save_cache(cache)
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

def calculate_vwap(stock_data: StockData) -> StockData:
    stock_data.data['VWAP'] = (stock_data.data['Close'] * stock_data.data['Volume']).cumsum() / stock_data.data['Volume'].cumsum()
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

def plot_vwap(stock_data: StockData):
    plt.figure(figsize=(10, 5))
    plt.plot(stock_data.data['Close'], label=f'{stock_data.ticker} Closing Price', color='blue')
    plt.plot(stock_data.data['VWAP'], label='VWAP', linestyle='--', color='green')
    plt.title(f'{stock_data.ticker} Volume-Weighted Average Price (VWAP)')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid()
    plt.show()

# ----------------------------- INTERACTIVE GRAPHS -----------------------------

def plot_interactive(stock_data: StockData):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=stock_data.data.index,
        open=stock_data.data['Open'],
        high=stock_data.data['High'],
        low=stock_data.data['Low'],
        close=stock_data.data['Close'],
        name='Candlestick'
    ))
    fig.update_layout(
        title=f"{stock_data.ticker} Interactive Candlestick",
        xaxis_title="Date",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False  # Hides the range slider
    )
    fig.show()

# ----------------------------- MAIN FUNCTION -----------------------------

def main(ticker: str):
    stock_data = fetch_stock_data(ticker)
    if stock_data is None:
        return

    stock_data = detect_trend(stock_data)
    stock_data = calculate_rsi(stock_data)
    stock_data = calculate_macd(stock_data)
    stock_data = calculate_bollinger_bands(stock_data)
    stock_data = calculate_vwap(stock_data)

    # Plotting
    plot_trend(stock_data)
    plot_rsi(stock_data)
    plot_macd(stock_data)
    plot_bollinger_bands(stock_data)
    plot_candlestick(stock_data)
    plot_vwap(stock_data)
    plot_interactive(stock_data)

if __name__ == "__main__":
    stock_ticker = input("Enter stock ticker: ")
    main(stock_ticker)
