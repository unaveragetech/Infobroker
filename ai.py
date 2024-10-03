import json
import os
import csv
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import time
import random
import asyncio
import aiohttp
import aiofiles
import logging
from aiohttp import ClientSession, ClientTimeout
from typing import Set
from datetime import datetime

# Configure logging
logging.basicConfig(
    filename='stock_check.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Constants
CACHE_FILE = 'stock_cache.json'
LOG_FILE = 'ticker_log.txt'
FAILED_TICKERS_FILE = 'failed_tickers.txt'
INCOMPLETE_TICKERS_FILE = 'incomplete_tickers.json'
CSV_OUTPUT_FILE = 'stock_symbols_check.csv'
OFFICIAL_LISTINGS_URLS = {
    'NASDAQ': 'https://ftp.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt',
    'NYSE': 'https://ftp.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt'
}
HEADERS_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)"
    " Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko)"
    " Version/14.0.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)"
    " Chrome/91.0.4472.114 Safari/537.36",
]

# Load or initialize cache
def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(data: dict):
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_incomplete_tickers() -> dict:
    if os.path.exists(INCOMPLETE_TICKERS_FILE):
        with open(INCOMPLETE_TICKERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_incomplete_tickers(data: dict):
    with open(INCOMPLETE_TICKERS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

async def fetch_official_listings() -> Set[str]:
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
                logging.error(f"Error fetching listings from {exchange}: {e}")
    return symbols

def is_valid_ticker(ticker: str) -> bool:
    return 1 <= len(ticker) <= 7 and ticker.isupper() and ticker.isalpha()

async def check_stock_symbol_yf(symbol: str) -> str:
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        if 'symbol' in info and info['symbol'].upper() == symbol.upper():
            return f"Valid symbol. Company: {info.get('longName', 'N/A')}"
        else:
            return "Not a valid symbol"
    except Exception as e:
        logging.error(f"yfinance error for {symbol}: {e}")
        return f"Error checking symbol: {str(e)}"

async def fetch(session: ClientSession, url: str) -> str:
    try:
        async with session.get(url, timeout=ClientTimeout(total=10)) as response:
            response.raise_for_status()
            return await response.text()
    except Exception as e:
        logging.error(f"HTTP error fetching {url}: {e}")
        return ""

async def query_search_engine(session: ClientSession, stock_symbol: str, engine: str) -> str:
    if engine.lower() == 'google':
        url = f"https://www.google.com/search?q={stock_symbol}+stock"
        result_div_class = 'BNeawe s3v9rd AP7Wnd'
    elif engine.lower() == 'bing':
        url = f"https://www.bing.com/search?q={stock_symbol}+stock"
        result_div_class = 'b_snippet'
    elif engine.lower() == 'yahoo':
        url = f"https://finance.yahoo.com/quote/{stock_symbol}"
        result_div_class = 'D(ib) Fz(18px)'
    else:
        return "Unsupported search engine"

    headers = {
        "User-Agent": random.choice(HEADERS_LIST),
    }

    try:
        async with session.get(url, headers=headers, timeout=ClientTimeout(total=10)) as response:
            response.raise_for_status()
            text = await response.text()
            soup = BeautifulSoup(text, 'html.parser')
            result = soup.find('div', class_=result_div_class)
            if result:
                return result.get_text(strip=True)
            else:
                # Try alternative selectors
                if engine.lower() == 'google':
                    result = soup.find('div', class_='BNeawe iBp4i AP7Wnd')
                elif engine.lower() == 'bing':
                    result = soup.find('span', class_='b_algo')
                elif engine.lower() == 'yahoo':
                    result = soup.find('h1', {'data-reactid': '7'})
                if result:
                    return result.get_text(strip=True)
                return "No information found"
    except Exception as e:
        logging.error(f"Error querying {engine} for {stock_symbol}: {e}")
        return f"Error querying {engine}: {str(e)}"

async def query_all_search_engines(session: ClientSession, stock_symbol: str) -> dict:
    engines = ['Google', 'Bing', 'Yahoo']
    tasks = [query_search_engine(session, stock_symbol, engine) for engine in engines]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    result = {}
    for engine, response in zip(engines, responses):
        if isinstance(response, Exception):
            result[engine] = f"Error: {str(response)}"
        else:
            result[engine] = response
    return result

async def write_csv_header():
    async with aiofiles.open(CSV_OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
        # Directly write the header to the CSV file
        await csvfile.write('Symbol,Yahoo Finance Status,Google Response,Bing Response,Yahoo Finance Response\n')

async def write_csv_row(row: list):
    async with aiofiles.open(CSV_OUTPUT_FILE, 'a', newline='', encoding='utf-8') as csvfile:
        # Directly write the row to the CSV file
        await csvfile.write(','.join(row) + '\n')

async def check_symbol(session: ClientSession, symbol: str, official_symbols: Set[str], cache: dict):
    logging.info(f"Checking symbol: {symbol}")
    yf_response = await check_stock_symbol_yf(symbol)

    if "Valid symbol" not in yf_response and symbol in official_symbols:
        search_responses = await query_all_search_engines(session, symbol)
    else:
        search_responses = {'Google': 'N/A', 'Bing': 'N/A', 'Yahoo': 'N/A'}

    # Update cache
    cache[symbol] = {
        'yfinance': yf_response,
        'google': search_responses.get('Google', ''),
        'bing': search_responses.get('Bing', ''),
        'yahoo_finance': search_responses.get('Yahoo', ''),
        'last_checked': datetime.now().isoformat()
    }

    # Write to CSV
    row = [
        symbol,
        yf_response,
        search_responses.get('Google', ''),
        search_responses.get('Bing', ''),
        search_responses.get('Yahoo', '')
    ]
    await write_csv_row(row)

    # Random delay to mimic human behavior and avoid rate limiting
    await asyncio.sleep(random.uniform(1, 3))

async def main():
    # Load data
    cache = load_cache()
    incomplete_tickers = load_incomplete_tickers()

    # Fetch official listings
    official_symbols = await fetch_official_listings()
    logging.info(f"Fetched {len(official_symbols)} official symbols.")

    # Prepare CSV
    await write_csv_header()

    # Initialize aiohttp session
    timeout = ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = []
        for symbol in incomplete_tickers.keys():
            if symbol not in cache:
                tasks.append(check_symbol(session, symbol, official_symbols, cache))
        
        # Limit concurrency to prevent overwhelming the system and being blocked
        semaphore = asyncio.Semaphore(10)

        async def sem_task(task):
            async with semaphore:
                await task

        await asyncio.gather(*[sem_task(task) for task in tasks])

    # Save updated cache
    save_cache(cache)
    save_incomplete_tickers(incomplete_tickers)

    logging.info("CSV file has been created: stock_symbols_check.csv")
    print("CSV file has been created: stock_symbols_check.csv")

if __name__ == "__main__":
    asyncio.run(main())
