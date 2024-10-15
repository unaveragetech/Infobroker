import json
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
from datetime import datetime, timedelta

# Load stock cache from JSON file
def load_stock_cache(filename='stock_cache.json'):
    with open(filename, 'r') as file:
        stocks = json.load(file)
    return stocks

# Fetch stock data from yfinance
def fetch_stock_data(symbol, start_date, end_date):
    stock_data = yf.download(symbol, start=start_date, end=end_date)
    return stock_data

# Generate various stock charts
def line_chart(stock_data, symbol):
    plt.figure(figsize=(10, 5))
    plt.plot(stock_data['Close'], label='Close Price')
    plt.title(f'{symbol} Line Chart')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid()
    plt.savefig(f'{symbol}_line_chart.png')
    plt.close()

def moving_average_chart(stock_data, symbol):
    stock_data['MA50'] = stock_data['Close'].rolling(window=50).mean()
    plt.figure(figsize=(10, 5))
    plt.plot(stock_data['Close'], label='Close Price')
    plt.plot(stock_data['MA50'], label='50-Day MA', color='orange')
    plt.title(f'{symbol} Moving Average Chart')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid()
    plt.savefig(f'{symbol}_moving_average_chart.png')
    plt.close()

def bollinger_bands_chart(stock_data, symbol):
    stock_data['MA20'] = stock_data['Close'].rolling(window=20).mean()
    stock_data['Upper'] = stock_data['MA20'] + (stock_data['Close'].rolling(window=20).std() * 2)
    stock_data['Lower'] = stock_data['MA20'] - (stock_data['Close'].rolling(window=20).std() * 2)
    plt.figure(figsize=(10, 5))
    plt.plot(stock_data['Close'], label='Close Price')
    plt.plot(stock_data['Upper'], label='Upper Band', linestyle='--', color='red')
    plt.plot(stock_data['Lower'], label='Lower Band', linestyle='--', color='red')
    plt.fill_between(stock_data.index, stock_data['Upper'], stock_data['Lower'], color='gray', alpha=0.1)
    plt.title(f'{symbol} Bollinger Bands Chart')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid()
    plt.savefig(f'{symbol}_bollinger_bands_chart.png')
    plt.close()

def rsi_chart(stock_data, symbol):
    delta = stock_data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    plt.figure(figsize=(10, 5))
    plt.plot(rsi, label='RSI', color='purple')
    plt.axhline(70, linestyle='--', color='red')
    plt.axhline(30, linestyle='--', color='green')
    plt.title(f'{symbol} RSI Chart')
    plt.xlabel('Date')
    plt.ylabel('RSI')
    plt.legend()
    plt.grid()
    plt.savefig(f'{symbol}_rsi_chart.png')
    plt.close()

def candlestick_chart(stock_data, symbol):
    import mplfinance as mpf
    mpf.plot(stock_data, type='candle', volume=True, title=f'{symbol} Candlestick Chart', savefig=f'{symbol}_candlestick_chart.png')

def volume_chart(stock_data, symbol):
    plt.figure(figsize=(10, 5))
    plt.bar(stock_data.index, stock_data['Volume'], color='blue')
    plt.title(f'{symbol} Volume Chart')
    plt.xlabel('Date')
    plt.ylabel('Volume')
    plt.grid()
    plt.savefig(f'{symbol}_volume_chart.png')
    plt.close()

def ema_chart(stock_data, symbol):
    stock_data['EMA'] = stock_data['Close'].ewm(span=20, adjust=False).mean()
    plt.figure(figsize=(10, 5))
    plt.plot(stock_data['Close'], label='Close Price')
    plt.plot(stock_data['EMA'], label='20-Day EMA', color='orange')
    plt.title(f'{symbol} EMA Chart')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid()
    plt.savefig(f'{symbol}_ema_chart.png')
    plt.close()

def stochastic_oscillator_chart(stock_data, symbol):
    stock_data['L14'] = stock_data['Low'].rolling(window=14).min()
    stock_data['H14'] = stock_data['High'].rolling(window=14).max()
    stock_data['%K'] = 100 * (stock_data['Close'] - stock_data['L14']) / (stock_data['H14'] - stock_data['L14'])
    stock_data['%D'] = stock_data['%K'].rolling(window=3).mean()
    
    plt.figure(figsize=(10, 5))
    plt.plot(stock_data['%K'], label='%K', color='blue')
    plt.plot(stock_data['%D'], label='%D', color='orange')
    plt.axhline(80, linestyle='--', color='red')
    plt.axhline(20, linestyle='--', color='green')
    plt.title(f'{symbol} Stochastic Oscillator Chart')
    plt.xlabel('Date')
    plt.ylabel('Value')
    plt.legend()
    plt.grid()
    plt.savefig(f'{symbol}_stochastic_oscillator_chart.png')
    plt.close()

def macd_chart(stock_data, symbol):
    stock_data['EMA12'] = stock_data['Close'].ewm(span=12, adjust=False).mean()
    stock_data['EMA26'] = stock_data['Close'].ewm(span=26, adjust=False).mean()
    stock_data['MACD'] = stock_data['EMA12'] - stock_data['EMA26']
    stock_data['Signal'] = stock_data['MACD'].ewm(span=9, adjust=False).mean()

    plt.figure(figsize=(10, 5))
    plt.plot(stock_data['MACD'], label='MACD', color='blue')
    plt.plot(stock_data['Signal'], label='Signal Line', color='orange')
    plt.title(f'{symbol} MACD Chart')
    plt.xlabel('Date')
    plt.ylabel('Value')
    plt.legend()
    plt.grid()
    plt.savefig(f'{symbol}_macd_chart.png')
    plt.close()

def correlation_heatmap(stock_data, symbol):
    correlation = stock_data.corr()
    plt.figure(figsize=(10, 8))
    sns.heatmap(correlation, annot=True, fmt='.2f', cmap='coolwarm', square=True)
    plt.title(f'{symbol} Correlation Heatmap')
    plt.savefig(f'{symbol}_correlation_heatmap.png')
    plt.close()

def price_histogram(stock_data, symbol):
    plt.figure(figsize=(10, 5))
    plt.hist(stock_data['Close'], bins=20, color='blue', alpha=0.7)
    plt.title(f'{symbol} Price Histogram')
    plt.xlabel('Price')
    plt.ylabel('Frequency')
    plt.grid()
    plt.savefig(f'{symbol}_price_histogram.png')
    plt.close()

def percentage_change_chart(stock_data, symbol):
    percentage_change = stock_data['Close'].pct_change() * 100
    plt.figure(figsize=(10, 5))
    plt.plot(percentage_change, label='Percentage Change', color='blue')
    plt.title(f'{symbol} Percentage Change Chart')
    plt.xlabel('Date')
    plt.ylabel('Percentage Change (%)')
    plt.legend()
    plt.grid()
    plt.savefig(f'{symbol}_percentage_change_chart.png')
    plt.close()

def drawdown_chart(stock_data, symbol):
    cumulative_return = (1 + stock_data['Close'].pct_change()).cumprod()
    drawdown = (cumulative_return.cummax() - cumulative_return) / cumulative_return.cummax()
    
    plt.figure(figsize=(10, 5))
    plt.plot(drawdown, label='Drawdown', color='purple')
    plt.title(f'{symbol} Drawdown Chart')
    plt.xlabel('Date')
    plt.ylabel('Drawdown')
    plt.legend()
    plt.grid()
    plt.savefig(f'{symbol}_drawdown_chart.png')
    plt.close()

def vwap_chart(stock_data, symbol):
    vwap = (stock_data['Volume'] * (stock_data['High'] + stock_data['Low'] + stock_data['Close']) / 3).cumsum() / stock_data['Volume'].cumsum()
    plt.figure(figsize=(10, 5))
    plt.plot(vwap, label='VWAP', color='purple')
    plt.title(f'{symbol} VWAP Chart')
    plt.xlabel('Date')
    plt.ylabel('VWAP')
    plt.legend()
    plt.grid()
    plt.savefig(f'{symbol}_vwap_chart.png')
    plt.close()

# CLI menu function
def cli_menu():
    while True:
        print("\nStock Analysis CLI")
        print("1. Load Stock Cache")
        print("2. Fetch Stock Data")
        print("3. Generate Line Chart")
        print("4. Generate Moving Average Chart")
        print("5. Generate Bollinger Bands Chart")
        print("6. Generate RSI Chart")
        print("7. Generate Candlestick Chart")
        print("8. Generate Volume Chart")
        print("9. Generate EMA Chart")
        print("10. Generate Stochastic Oscillator Chart")
        print("11. Generate MACD Chart")
        print("12. Generate Correlation Heatmap")
        print("13. Generate Price Histogram")
        print("14. Generate Percentage Change Chart")
        print("15. Generate Drawdown Chart")
        print("16. Generate VWAP Chart")
        print("0. Exit")
        
        choice = input("Choose an option: ")

        if choice == '1':
            stocks = load_stock_cache()
            print("Available stocks:")
            for symbol in stocks:
                print(symbol)

        elif choice == '2':
            symbol = input("Enter stock symbol: ")
            days = int(input("Enter number of days to fetch data for (default is 30): ") or 30)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            stock_data = fetch_stock_data(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            print(stock_data)

        elif choice in ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16']:
            symbol = input("Enter stock symbol: ")
            days = int(input("Enter number of days to fetch data for (default is 30): ") or 30)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            stock_data = fetch_stock_data(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

            if choice == '3':
                line_chart(stock_data, symbol)
            elif choice == '4':
                moving_average_chart(stock_data, symbol)
            elif choice == '5':
                bollinger_bands_chart(stock_data, symbol)
            elif choice == '6':
                rsi_chart(stock_data, symbol)
            elif choice == '7':
                candlestick_chart(stock_data, symbol)
            elif choice == '8':
                volume_chart(stock_data, symbol)
            elif choice == '9':
                ema_chart(stock_data, symbol)
            elif choice == '10':
                stochastic_oscillator_chart(stock_data, symbol)
            elif choice == '11':
                macd_chart(stock_data, symbol)
            elif choice == '12':
                correlation_heatmap(stock_data, symbol)
            elif choice == '13':
                price_histogram(stock_data, symbol)
            elif choice == '14':
                percentage_change_chart(stock_data, symbol)
            elif choice == '15':
                drawdown_chart(stock_data, symbol)
            elif choice == '16':
                vwap_chart(stock_data, symbol)

        elif choice == '0':
            break
        else:
            print("Invalid option, please try again.")

if __name__ == "__main__":
    cli_menu()
