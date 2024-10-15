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
#-------------------------------------------------------------
#
### Table: Ticker Generation Queries
#
# | **Function Name**                     | **Description**                                                                                                 | **Full Function Code**                                                                                                                                                                                                                                                                                                                                                                                                                       | **Example Use Case**                                                                 |
# |---------------------------------------|-------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
# | `generate_us_stock_ticker`           | Generates a random ticker for US stock exchanges with optional suffixes like `NYSE`, `NASDAQ`, and `US`.       | ```python\ndef generate_us_stock_ticker(min_length=1, max_length=4, prefix='', suffix='US', exclude_tickers=None, allowed_suffixes=['US', 'NYSE', 'NASDAQ']):\n    return generate_random_ticker(min_length, max_length, prefix, suffix, exclude_tickers, allowed_suffixes=allowed_suffixes)\n```                                                                                                                                               | For general US stocks (e.g., `AAPL`, `GOOG`).                                      |
# | `generate_eu_stock_ticker`           | Generates a random ticker for European stock exchanges, using suffixes for specific exchanges like `.LSE`, `.FR`. | ```python\ndef generate_eu_stock_ticker(min_length=2, max_length=5, prefix='', suffix='', exclude_tickers=None, allowed_exchanges=['LSE', 'FR', 'DE']):\n    return generate_random_ticker(min_length, max_length, prefix, suffix, exclude_tickers, allowed_exchanges=allowed_exchanges)\n```                                                                                                                                                      | For European stocks (e.g., `HSBA.LSE`, `BNP.FR`).                                  |
# | `generate_tech_stock_ticker`         | Generates ticker symbols for technology companies, usually 2-4 characters.                                    | ```python\ndef generate_tech_stock_ticker(min_length=2, max_length=4, prefix='', suffix='', exclude_tickers=None):\n    return generate_random_ticker(min_length, max_length, prefix, suffix, exclude_tickers)\n```                                                                                                                                                                                                                                  | Suitable for tech companies listed on US or global markets (e.g., `MSFT`, `GOOG`). |
# | `generate_bond_ticker`                | Generates ticker symbols for bonds or fixed-income securities, using `.BOND` as a suffix.                      | ```python\ndef generate_bond_ticker(min_length=3, max_length=5, prefix='', suffix='BOND', exclude_tickers=None):\n    return generate_random_ticker(min_length, max_length, prefix, suffix, exclude_tickers)\n```                                                                                                                                                                                                                                     | For bond markets (e.g., `T10Y.BOND`).                                              |
# | `generate_crypto_ticker`              | Generates ticker symbols for cryptocurrencies, usually 3-5 characters.                                         | ```python\ndef generate_crypto_ticker(min_length=3, max_length=5, prefix='', suffix='', exclude_tickers=None):\n    return generate_random_ticker(min_length, max_length, prefix, suffix, exclude_tickers)\n```                                                                                                                                                                                                                                      | For cryptocurrency tickers (e.g., `BTC`, `ETH`).                                  |
# | `generate_health_stock_ticker`        | Generates ticker symbols for healthcare companies, commonly using 3-5 characters.                           | ```python\ndef generate_health_stock_ticker(min_length=3, max_length=5, prefix='', suffix='', exclude_tickers=None):\n    return generate_random_ticker(min_length, max_length, prefix, suffix, exclude_tickers)\n```                                                                                                                                                                                                                                | For healthcare stocks (e.g., `PFE`, `JNJ`).                                        |
# | `generate_luxury_brand_ticker`        | Generates tickers for luxury goods companies, allowing for longer names and global exchanges like `.FR`, `.IT`. | ```python\ndef generate_luxury_brand_ticker(min_length=4, max_length=6, prefix='', suffix='', exclude_tickers=None, allowed_exchanges=['FR', 'IT']):\n    return generate_random_ticker(min_length, max_length, prefix, suffix, exclude_tickers, allowed_exchanges=allowed_exchanges)\n```                                                                                                                                                         | For luxury brands listed on international markets (e.g., `LVMH.FR`).               |
# | `generate_energy_stock_ticker`        | Generates ticker symbols for energy companies, typically 3-5 characters, with suffix options like `.OIL`, `.GAS`. | ```python\ndef generate_energy_stock_ticker(min_length=3, max_length=5, prefix='', suffix='', exclude_tickers=None, allowed_suffixes=['OIL', 'GAS']):\n    return generate_random_ticker(min_length, max_length, prefix, suffix, exclude_tickers, allowed_suffixes=allowed_suffixes)\n```                                                                                                                                                        | For energy sector stocks (e.g., `XOM.OIL`, `BP.GAS`).                             |
# | `generate_fintech_stock_ticker`      | Generates ticker symbols for fintech companies, typically 4-5 characters.                                    | ```python\ndef generate_fintech_stock_ticker(min_length=4, max_length=5, prefix='', suffix='', exclude_tickers=None):\n    return generate_random_ticker(min_length, max_length, prefix, suffix, exclude_tickers)\n```                                                                                                                                                                                                                              | For fintech stocks (e.g., `PYPL`, `SQ`).                                           |
#
#
#--------------------------------------------------------------

# Cache and logging functions
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

def generate_random_ticker(min_length=1, max_length=7, prefix='', suffix='', 
                           exclude_tickers=None, allowed_exchanges=None, 
                           allowed_suffixes=None):
    """
    Generates a random ticker symbol based on specified criteria.
    
    Parameters:
    - min_length: Minimum length of the ticker (default 1).
    - max_length: Maximum length of the ticker (default 7).
    - prefix: String prefix for the ticker (default '').
    - suffix: String suffix for the ticker (default 'US').
    - exclude_tickers: A set of tickers to exclude from generation (default None).
    - allowed_exchanges: A list of allowed stock exchange codes (default None).
    - allowed_suffixes: A list of allowed suffixes for ticker validation (default None).
    
    Returns:
    - A valid ticker symbol as a string.
    """
    
    # Load failed tickers to exclude from generation
    excluded_tickers = exclude_tickers if exclude_tickers else set()
    if os.path.exists(FAILED_TICKERS_FILE):
        with open(FAILED_TICKERS_FILE, 'r') as f:
            excluded_tickers.update(line.strip().upper() for line in f)
    
    # If specific suffixes are allowed, validate suffix
    if allowed_suffixes and suffix not in allowed_suffixes:
        suffix = random.choice(allowed_suffixes)
    
    while True:
        # Generate random ticker of specified length
        length = random.randint(min_length, max_length)
        main_ticker = ''.join(random.choices(string.ascii_uppercase, k=length))
        
        # Construct the full ticker with prefix and suffix
        full_ticker = f"{prefix}{main_ticker}{suffix}".upper()

        # Check if the ticker meets exchange criteria (if any)
        if allowed_exchanges:
            exchange_code = random.choice(allowed_exchanges)
            full_ticker = f"{full_ticker}.{exchange_code}"
        
        # Validate the ticker
        if full_ticker not in excluded_tickers and is_valid_ticker(full_ticker):
            return full_ticker


def is_valid_ticker(ticker):
    if len(ticker) < 1 or len(ticker) > 5:
        return False
    if not all(char.isupper() for char in ticker):
        return False
    return True

def is_ticker_incomplete(ticker_data):
    important_fields = ['name', 'market_cap', 'sector', 'industry', 'exchange', 'currency', 'country', 'website']
    return any(ticker_data.get(field) in ['N/A', None] for field in important_fields)

# Ticker management functions
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
        print("\n--- Ticker Management System ---")
        print("1. Find and add new tickers")
        print("2. Update and fix cache")
        print("3. Fix incomplete tickers")
        print("4. View cache statistics")
        print("5. Exit")

        user_input = input("Enter your choice (1-5): ").strip()

        if user_input == '1':
            try:
                num_tickers = int(input("Enter the number of new tickers to find: ").strip())
                if num_tickers < 0:
                    print("Please enter a positive number.")
                    continue
                find_and_add_tickers(num_tickers)
            except ValueError:
                print("Invalid input. Please enter a valid number.")
        elif user_input == '2':
            update_stock_cache_info()
        elif user_input == '3':
            attempt_fix_incomplete_tickers()
        elif user_input == '4':
            cache = load_cache()
            incomplete_tickers = load_incomplete_tickers()
            print(f"Cache contains {len(cache)} valid tickers.")
            print(f"There are {len(incomplete_tickers)} incomplete tickers.")
        elif user_input == '5':
            print("Exiting the program.")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == '__main__':
    main()
