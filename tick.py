import yfinance as yf
import json
import os
from datetime import datetime
import random
import string

CACHE_FILE = 'stock_cache.json'
LOG_FILE = 'ticker_log.txt'
FAILED_TICKERS_FILE = 'failed_tickers.txt'
INCOMPLETE_TICKERS_FILE = 'incomplete_tickers.json'

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_cache(data):
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def load_incomplete_tickers():
    if os.path.exists(INCOMPLETE_TICKERS_FILE):
        with open(INCOMPLETE_TICKERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_incomplete_tickers(data):
    with open(INCOMPLETE_TICKERS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def log_ticker(ticker, status):
    with open(LOG_FILE, 'a') as f:
        f.write(f"{datetime.now().isoformat()}: {ticker} - {status}\n")

def save_failed_ticker(ticker):
    with open(FAILED_TICKERS_FILE, 'a') as f:
        f.write(f"{ticker}\n")

def generate_random_ticker():
    length = random.randint(2, 4)
    return ''.join(random.choices(string.ascii_uppercase, k=length))

def is_ticker_incomplete(ticker_data):
    important_fields = ['name', 'market_cap', 'sector', 'industry', 'exchange', 'currency', 'country', 'website']
    return any(ticker_data.get(field) in ['N/A', None] for field in important_fields)

def validate_and_add_ticker(ticker):
    cache = load_cache()
    incomplete_tickers = load_incomplete_tickers()
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        if info and 'symbol' in info:
            ticker_data = {
                "name": info.get('longName', ticker),
                "market_cap": info.get('marketCap', 'N/A'),
                "sector": info.get('sector', 'N/A'),
                "industry": info.get('industry', 'N/A'),
                "currency": info.get('currency', 'N/A'),
                "exchange": info.get('exchange', 'N/A'),
                "country": info.get('country', 'N/A'),
                "website": info.get('website', 'N/A'),
                "viewed": False,
                "last_updated": datetime.now().isoformat()
            }
            
            if is_ticker_incomplete(ticker_data):
                incomplete_tickers[ticker] = ticker_data
                save_incomplete_tickers(incomplete_tickers)
                log_ticker(ticker, "Incomplete data. Added to incomplete_tickers.json")
                print(f"Incomplete data for ticker: {ticker}. Added to incomplete_tickers.json")
                return False
            
            cache[ticker] = ticker_data
            save_cache(cache)
            log_ticker(ticker, "Valid and added to cache")
            print(f"Found valid ticker: {ticker}")
            print(f"Name: {ticker_data['name']}")
            print(f"Market Cap: {ticker_data['market_cap']}")
            print(f"Sector: {ticker_data['sector']}")
            print(f"Industry: {ticker_data['industry']}")
            print(f"Exchange: {ticker_data['exchange']}")
            print(f"Currency: {ticker_data['currency']}")
            print(f"Country: {ticker_data['country']}")
            print(f"Website: {ticker_data['website']}")
            print(f"Saved to: {CACHE_FILE}")
            return True
        else:
            log_ticker(ticker, "Invalid ticker")
            print(f"Invalid ticker: {ticker}")
            save_failed_ticker(ticker)
            return False
    except Exception as e:
        log_ticker(ticker, f"Error: {str(e)}")
        print(f"Error processing ticker {ticker}: {str(e)}")
        save_failed_ticker(ticker)
        return False

def find_and_add_tickers(num_tickers):
    added_count = 0
    attempts = 0
    max_attempts = num_tickers * 10  # Limit the number of attempts

    while added_count < num_tickers and attempts < max_attempts:
        ticker = generate_random_ticker()
        print(f"Attempting ticker: {ticker}")
        if validate_and_add_ticker(ticker):
            added_count += 1
            print(f"Progress: {added_count}/{num_tickers}")
        attempts += 1

    print(f"Added {added_count} new tickers to the cache after {attempts} attempts.")
    print(f"Failed tickers have been saved to {FAILED_TICKERS_FILE}")

def update_stock_cache_info():
    cache = load_cache()
    incomplete_tickers = load_incomplete_tickers()
    updated_count = 0
    removed_count = 0
    incomplete_count = 0

    for ticker in list(cache.keys()):
        print(f"Checking ticker: {ticker}")
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if info and 'symbol' in info:
                ticker_data = {
                    "name": info.get('longName', ticker),
                    "market_cap": info.get('marketCap', 'N/A'),
                    "sector": info.get('sector', 'N/A'),
                    "industry": info.get('industry', 'N/A'),
                    "currency": info.get('currency', 'N/A'),
                    "exchange": info.get('exchange', 'N/A'),
                    "country": info.get('country', 'N/A'),
                    "website": info.get('website', 'N/A'),
                    "viewed": cache[ticker].get('viewed', False),
                    "last_updated": datetime.now().isoformat()
                }
                
                if any(value == 'N/A' for key, value in ticker_data.items() if key not in ['viewed', 'last_updated']):
                    incomplete_tickers[ticker] = ticker_data
                    del cache[ticker]
                    incomplete_count += 1
                    print(f"Moved incomplete ticker to incomplete_tickers.json: {ticker}")
                else:
                    cache[ticker] = ticker_data
                    updated_count += 1
                    print(f"Updated information for {ticker}")
            else:
                del cache[ticker]
                removed_count += 1
                print(f"Removed invalid ticker: {ticker}")
        except Exception as e:
            print(f"Error processing {ticker}: {str(e)}")
            incomplete_tickers[ticker] = cache[ticker]
            del cache[ticker]
            incomplete_count += 1

    save_cache(cache)
    save_incomplete_tickers(incomplete_tickers)
    print(f"Updated information for {updated_count} stocks in the cache.")
    print(f"Removed {removed_count} invalid stocks from the cache.")
    print(f"Moved {incomplete_count} incomplete tickers to {INCOMPLETE_TICKERS_FILE}")

def attempt_fix_incomplete_tickers():
    incomplete_tickers = load_incomplete_tickers()
    fixed_count = 0

    for ticker in list(incomplete_tickers.keys()):
        print(f"Attempting to fix: {ticker}")
        if validate_and_add_ticker(ticker):
            del incomplete_tickers[ticker]
            fixed_count += 1
        else:
            alternative_ticker = input(f"Enter alternative ticker for {ticker} (or press Enter to skip): ").strip().upper()
            if alternative_ticker and validate_and_add_ticker(alternative_ticker):
                del incomplete_tickers[ticker]
                fixed_count += 1

    save_incomplete_tickers(incomplete_tickers)
    print(f"Fixed {fixed_count} incomplete tickers.")
    print(f"{len(incomplete_tickers)} tickers remain incomplete.")

def main():
    while True:
        try:
            print("\n--- Ticker Management System ---")
            print("1. Find and add new tickers")
            print("2. Update and fix cache")
            print("3. Fix incomplete tickers")
            print("4. View cache statistics")
            print("5. Exit")
            user_input = input("Enter your choice (1-5): ")
            
            if user_input == '1':
                num_tickers = int(input("Enter the number of new tickers to find: "))
                if num_tickers < 0:
                    print("Please enter a positive number.")
                    continue
                find_and_add_tickers(num_tickers)
            elif user_input == '2':
                update_stock_cache_info()
            elif user_input == '3':
                attempt_fix_incomplete_tickers()
            elif user_input == '4':
                cache = load_cache()
                incomplete = load_incomplete_tickers()
                print(f"Total tickers in cache: {len(cache)}")
                print(f"Total incomplete tickers: {len(incomplete)}")
                with open(FAILED_TICKERS_FILE, 'r') as f:
                    failed_count = sum(1 for _ in f)
                print(f"Total failed tickers: {failed_count}")
            elif user_input == '5':
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please enter a number between 1 and 5.")
        except ValueError:
            print("Please enter a valid number.")

if __name__ == "__main__":
    main()