import json
import os
import csv
import yfinance as yf
import aiohttp
import aiofiles
import logging
import asyncio
import random
from datetime import datetime
from typing import Set, List, Dict
import pandas as pd
import matplotlib.pyplot as plt

# ---------------------------- Section 1: Configuration and Setup ----------------------------

# Logging configuration
logging.basicConfig(
    filename='stock_check.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Constants
CACHE_FILE = 'stock_cache.json'
CSV_OUTPUT_FILE = 'stock_data_analysis.csv'
OFFICIAL_LISTINGS_URLS = {
    'NASDAQ': 'https://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt',
    'NYSE': 'https://ftp.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt'
}

# ---------------------------- Section 2: Caching Functions ----------------------------

def load_cache() -> dict:
    """Load cached stock data from CACHE_FILE."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logging.error("Cache file is corrupted. Initializing empty cache.")
                return {}
    return {}

def save_cache(data: dict):
    """Save stock data to CACHE_FILE."""
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ---------------------------- Section 3: Ticker Validation and Insights ----------------------------

async def validate_ticker_yf(symbol: str) -> dict:
    """
    Validate ticker using yfinance and fetch detailed information and insights.
    """
    result = {
        "symbol": symbol.upper(),
        "status": "Unknown",
        "valid": False,
        "company": "N/A",
        "sector": "N/A",
        "marketCap": "N/A",
        "price": "N/A",
        "pe_ratio": "N/A",
        "dividend_yield": "N/A",
        "moving_average_50": "N/A",
        "moving_average_200": "N/A",
        "rsi": "N/A",
        "macd_line": "N/A",
        "signal_line": "N/A",
        "macd_histogram": "N/A"
    }
    
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # Check if symbol exists
        if 'symbol' in info and info['symbol'].upper() == symbol.upper():
            result["status"] = "Valid"
            result["valid"] = True
            result["company"] = info.get("longName", "N/A")
            result["sector"] = info.get("sector", "N/A")
            result["marketCap"] = info.get("marketCap", "N/A")
            
            # Fetch price
            hist = stock.history(period="1d")
            if not hist.empty:
                result["price"] = round(hist['Close'].iloc[-1], 2)
            
            # P/E Ratio
            result["pe_ratio"] = info.get("trailingPE", "N/A")
            
            # Dividend Yield
            dividend_yield = info.get("dividendYield", "N/A")
            if dividend_yield != "N/A":
                result["dividend_yield"] = round(dividend_yield * 100, 2)  # Convert to percentage
            
            # Moving Averages
            hist_50 = stock.history(period="50d")
            hist_200 = stock.history(period="200d")
            if not hist_50.empty:
                result["moving_average_50"] = round(hist_50['Close'].mean(), 2)
            if not hist_200.empty:
                result["moving_average_200"] = round(hist_200['Close'].mean(), 2)
            
            # RSI and MACD
            hist_full = stock.history(period="6mo")
            if not hist_full.empty:
                result["rsi"] = calculate_rsi(hist_full['Close'])
                macd = calculate_macd(hist_full['Close'])
                result["macd_line"] = round(macd['macd_line'], 2)
                result["signal_line"] = round(macd['signal_line'], 2)
                result["macd_histogram"] = round(macd['histogram'], 2)
        else:
            result["status"] = "Invalid"
    except Exception as e:
        logging.error(f"yfinance error for {symbol}: {e}")
        result["status"] = "Error"
    
    return result

def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calculate the Relative Strength Index (RSI) based on price history."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    if not rsi.empty:
        return round(rsi.iloc[-1], 2)
    return "N/A"

def calculate_macd(prices: pd.Series, short_period: int = 12, long_period: int = 26, signal_period: int = 9) -> dict:
    """Calculate MACD (Moving Average Convergence Divergence) indicator."""
    short_ema = prices.ewm(span=short_period, adjust=False).mean()
    long_ema = prices.ewm(span=long_period, adjust=False).mean()
    macd_line = short_ema - long_ema
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    macd_histogram = macd_line - signal_line
    return {
        "macd_line": macd_line.iloc[-1],
        "signal_line": signal_line.iloc[-1],
        "histogram": macd_histogram.iloc[-1]
    }

# ---------------------------- Section 4: Data Fetching ----------------------------

async def fetch_listing_symbols() -> Set[str]:
    """
    Fetch official stock symbols from NASDAQ and NYSE.
    """
    symbols = set()
    async with aiohttp.ClientSession() as session:
        for exchange, url in OFFICIAL_LISTINGS_URLS.items():
            try:
                async with session.get(url) as response:
                    text = await response.text()
                    lines = text.splitlines()
                    for line in lines[1:]:  # Skip header
                        parts = line.split('|')
                        symbol = parts[0].strip()
                        if symbol and symbol != 'Symbol':
                            symbols.add(symbol.upper())
            except Exception as e:
                logging.error(f"Error fetching {exchange} symbols: {e}")
    return symbols

# ---------------------------- Section 5: CSV Handling ----------------------------

async def write_csv_header():
    """Write the header to the CSV output file."""
    async with aiofiles.open(CSV_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        header = 'Symbol,Company,Sector,MarketCap,Price,PE_Ratio,Dividend_Yield,MA50,MA200,RSI,MACD_Line,Signal_Line,MACD_Histogram,Status\n'
        await f.write(header)

async def write_csv_row(result: dict):
    """Write a row of stock data to the CSV."""
    async with aiofiles.open(CSV_OUTPUT_FILE, 'a', encoding='utf-8') as f:
        row = [
            result["symbol"],
            f'"{result["company"]}"',  # Enclose in quotes in case of commas
            result["sector"],
            result["marketCap"],
            result["price"],
            result["pe_ratio"],
            result["dividend_yield"],
            result["moving_average_50"],
            result["moving_average_200"],
            result["rsi"],
            result["macd_line"],
            result["signal_line"],
            result["macd_histogram"],
            result["status"]
        ]
        await f.write(','.join(map(str, row)) + '\n')

# ---------------------------- Section 6: Processing Symbols ----------------------------

async def process_symbol(symbol: str, cache: dict):
    """Process and validate a single stock symbol."""
    if symbol in cache:
        logging.info(f"{symbol} already in cache. Skipping.")
        return
    result = await validate_ticker_yf(symbol)
    cache[symbol] = result
    save_cache(cache)
    await write_csv_row(result)

# ---------------------------- Section 7: CLI Interface ----------------------------

def display_stock_info(stock_info: dict):
    """Display detailed stock information."""
    print(f"\n--- {stock_info['symbol']} ---")
    print(f"Company: {stock_info['company']}")
    print(f"Sector: {stock_info['sector']}")
    print(f"Market Cap: {stock_info['marketCap']}")
    print(f"Current Price: ${stock_info['price']}")
    print(f"P/E Ratio: {stock_info['pe_ratio']}")
    print(f"Dividend Yield: {stock_info['dividend_yield']}%")
    print(f"50-Day Moving Average: ${stock_info['moving_average_50']}")
    print(f"200-Day Moving Average: ${stock_info['moving_average_200']}")
    print(f"RSI: {stock_info['rsi']}")
    print(f"MACD Line: {stock_info['macd_line']}")
    print(f"Signal Line: {stock_info['signal_line']}")
    print(f"MACD Histogram: {stock_info['macd_histogram']}")
    print(f"Status: {stock_info['status']}\n")

def plot_stock_data(stock_info: dict):
    """Generate and display plots for the stock."""
    symbol = stock_info['symbol']
    stock = yf.Ticker(symbol)
    hist = stock.history(period="1y")
    
    if hist.empty:
        print(f"No historical data available for {symbol}.")
        return
    
    # Plot Closing Price with Moving Averages
    plt.figure(figsize=(14, 7))
    plt.plot(hist['Close'], label='Closing Price', color='blue')
    if stock_info['moving_average_50'] != "N/A":
        plt.plot(hist['Close'].rolling(window=50).mean(), label='50-Day MA', color='red')
    if stock_info['moving_average_200'] != "N/A":
        plt.plot(hist['Close'].rolling(window=200).mean(), label='200-Day MA', color='green')
    plt.title(f"{symbol} Closing Price and Moving Averages")
    plt.xlabel("Date")
    plt.ylabel("Price ($)")
    plt.legend()
    plt.grid()
    plt.show()
    
    # Plot RSI
    plt.figure(figsize=(10, 4))
    prices = hist['Close']
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    plt.plot(rsi, label='RSI', color='purple')
    plt.axhline(70, color='red', linestyle='--', label='Overbought')
    plt.axhline(30, color='green', linestyle='--', label='Oversold')
    plt.title(f"{symbol} Relative Strength Index (RSI)")
    plt.xlabel("Date")
    plt.ylabel("RSI")
    plt.legend()
    plt.grid()
    plt.show()
    
    # Plot MACD
    plt.figure(figsize=(14, 7))
    short_ema = prices.ewm(span=12, adjust=False).mean()
    long_ema = prices.ewm(span=26, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal
    plt.plot(macd, label='MACD', color='blue')
    plt.plot(signal, label='Signal Line', color='red')
    plt.bar(hist.index, histogram, label='Histogram', color='grey')
    plt.title(f"{symbol} MACD")
    plt.xlabel("Date")
    plt.ylabel("MACD")
    plt.legend()
    plt.grid()
    plt.show()

def display_menu():
    """Display the main menu options."""
    print("\n--- Automated Information (ai.py) ---")
    print("1. Validate and Fetch Stock Data")
    print("2. View Cached Stock Information")
    print("3. Generate Stock Graphs")
    print("4. Exit")

def display_cached_symbols(cache: dict):
    """Display all cached stock symbols."""
    if not cache:
        print("No cached stock data available.")
        return
    print("\n--- Cached Stock Symbols ---")
    for i, symbol in enumerate(cache.keys(), start=1):
        print(f"{i}. {symbol}")
    print()

def select_symbols_from_cache(cache: dict) -> List[str]:
    """Allow user to select symbols from the cache."""
    if not cache:
        print("No cached stock data available.")
        return []
    
    symbols = list(cache.keys())
    display_cached_symbols(cache)
    
    selection = input("Enter the numbers of the stocks you want to select (comma-separated, e.g., 1,3,5): ")
    try:
        indices = [int(x.strip()) - 1 for x in selection.split(',')]
        selected_symbols = [symbols[i] for i in indices if 0 <= i < len(symbols)]
        if not selected_symbols:
            print("No valid symbols selected.")
        return selected_symbols
    except Exception as e:
        print("Invalid input. Please enter numbers separated by commas.")
        return []

def main_menu_actions(cache: dict):
    """Handle user actions based on menu selection."""
    while True:
        display_menu()
        choice = input("Enter your choice: ").strip()
        
        if choice == '1':
            asyncio.run(validate_and_fetch(cache))
        elif choice == '2':
            display_cached_symbols(cache)
        elif choice == '3':
            selected_symbols = select_symbols_from_cache(cache)
            for symbol in selected_symbols:
                if symbol in cache:
                    display_stock_info(cache[symbol])
                    plot_stock_data(cache[symbol])
                else:
                    print(f"Symbol {symbol} not found in cache.")
        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

# ---------------------------- Section 8: Validation and Fetching ----------------------------

async def validate_and_fetch(cache: dict):
    """Validate and fetch data for all symbols in cache or fetch new symbols."""
    # Fetch official symbols
    official_symbols = await fetch_listing_symbols()
    logging.info(f"Fetched {len(official_symbols)} official symbols.")
    
    # Prompt user to add new symbols or process existing cache
    print("\nDo you want to add new symbols to validate?")
    add_new = input("Enter 'y' to add new symbols, any other key to skip: ").lower()
    
    if add_new == 'y':
        new_symbols = input("Enter stock symbols separated by commas (e.g., AAPL, MSFT, GOOGL): ").upper()
        symbols = [sym.strip() for sym in new_symbols.split(',') if sym.strip()]
        for sym in symbols:
            if sym not in official_symbols:
                print(f"{sym} is not in the official listings. Skipping.")
                logging.warning(f"{sym} is not in the official listings.")
            else:
                if sym not in cache:
                    cache[sym] = {}  # Placeholder to mark as pending
    else:
        print("Skipping adding new symbols.")
    
    save_cache(cache)
    
    # Write CSV header if not exists
    if not os.path.exists(CSV_OUTPUT_FILE):
        await write_csv_header()
    
    # Process symbols concurrently
    tasks = []
    for symbol in official_symbols:
        if symbol not in cache or not cache[symbol].get('valid', False):
            tasks.append(process_symbol(symbol, cache))
    
    if tasks:
        print(f"Processing {len(tasks)} symbols. This may take a while...")
        await asyncio.gather(*tasks)
        print("Processing complete.")
    else:
        print("All symbols in cache are already validated and up-to-date.")

# ---------------------------- Section 9: Entry Point ----------------------------

def main():
    """Main entry point to run the CLI."""
    cache = load_cache()
    main_menu_actions(cache)

if __name__ == "__main__":
    main()
