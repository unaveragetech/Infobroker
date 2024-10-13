import yfinance as yf
import json
import os
import getpass
import random
from datetime import datetime

# Paths for storing user data and cache
USER_DATA_PATH = 'users.json'
CACHE_FILE = 'stock_cache.json'

# ----------------------------- CACHE MANAGEMENT -----------------------------

def initialize_cache():
    if not os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'w') as f:
            json.dump({}, f)

def load_cache():
    with open(CACHE_FILE, 'r') as f:
        return json.load(f)

def save_cache(data):
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f, indent=4)


#---------------------------------------------------
"""
    Fetch stock symbols from the specified exchange.
    
    Parameters:
    - exchange (str): The ticker symbol for the exchange. 
      Default is "^IXIC" (NASDAQ).
      
    Other options include:
    - "^GSPC": S&P 500
    - "^DJI": Dow Jones Industrial Average
    - "^RUT": Russell 2000
    - "^FTSE": FTSE 100 (UK)
    - "^N225": Nikkei 225 (Japan)
    - "^HSI": Hang Seng Index (Hong Kong)
    - "^AEX": AEX Index (Netherlands)
    - "^DAX": DAX Index (Germany)
    - "^IBEX": IBEX 35 (Spain)
    - "^TSX": S&P/TSX Composite Index (Canada)
    - "^BSESN": BSE Sensex (India)
    
    You can also use specific ETF tickers for broader market exposure, 
    such as "SPY" for S&P 500 or "QQQ" for NASDAQ-100.

    --def fetch_stock_symbols_from_exchange(Replace this below with an option above or from the exchange.txt file exchange=your replacement here):
    """
#----------------------------------------------------------
def fetch_stock_symbols_from_exchange(exchange="^IXIC"):
    try:
        # Fetching symbols based on the specified exchange
        exchange_ticker = yf.Ticker(exchange)
        symbols = exchange_ticker.info.get('components', [])

        # If no symbols are found, fall back to a default list
        if not symbols:
            print("No symbols fetched from the exchange. Using a default list.")
            symbols = get_default_symbols()
        
        return symbols[:100]  # Limit to 100 symbols for demonstration
    
    except Exception as e:
        print(f"Error fetching symbols: {e}")
        return get_default_symbols()

def get_default_symbols():
    # Default list of stock symbols
    return [
        "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "JNJ", "V",
        "BRK.B", "PG", "HD", "DIS", "PYPL", "NFLX", "CMCSA", "PEP", "INTC", "ADBE",
        "VZ", "CSCO", "T", "NKE", "XOM", "MRK", "KO", "PFE", "TGT", "ABT",
        "CVX", "WMT", "IBM", "CRM", "LLY", "PM", "TXN", "QCOM", "COST", "NVS",
        "MDT", "HON", "LMT", "AVGO", "AMGN", "SBUX", "NOW", "AMAT", "LRCX", "CAT",
        "UNH", "MO", "BKNG", "ADP", "SYK", "ANTM", "ISRG", "GILD", "CSX", "VRTX",
        "ATVI", "FIS", "FISV", "ZTS", "MET", "DHR", "SPGI", "TROW", "MCO", "MSCI",
        "CB", "ICE", "PNC", "USB", "NEM", "COP", "CARR", "KMB", "LNT", "SYF",
        "RMD", "EXC", "WBA", "MMC", "TAP", "HIG", "PXD", "ADI", "PSA", "ETR",
        "MDLZ", "DTE", "WDC", "LUMN", "NTRS", "HST", "FANG", "TTWO", "DLR", "O",
        "REXR", "ZBRA", "MPC", "MLM", "VTRS", "SRE", "CBRE", "KEYS", "DOV", "FMC"
    ]

def update_cache_with_symbols(symbols):
    cache = load_cache()
    for symbol in symbols:
        if symbol not in cache:
            try:
                stock_info = yf.Ticker(symbol).info
                cache[symbol] = {
                    "name": stock_info.get('longName', symbol),
                    "market_cap": stock_info.get('marketCap', 'N/A'),
                    "sector": stock_info.get('sector', 'N/A'),
                    "industry": stock_info.get('industry', 'N/A'),
                    "viewed": False
                }
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
    save_cache(cache)
    print(f"Added {len(symbols)} stock symbols to the cache.")

def cache_stocks():
    symbols = fetch_stock_symbols_from_exchange()
    update_cache_with_symbols(symbols)

def browse_stock_symbols(page=1, page_size=10):
    cache = load_cache()
    symbols = list(cache.keys())
    total_pages = len(symbols) // page_size + (1 if len(symbols) % page_size > 0 else 0)
    
    if page < 1:
        page = 1
    elif page > total_pages:
        page = total_pages

    start_index = (page - 1) * page_size
    end_index = start_index + page_size

    print(f"--- Page {page} of {total_pages} ---")
    for i, symbol in enumerate(symbols[start_index:end_index], start=start_index + 1):
        info = cache[symbol]
        print(f"{i}. {symbol}: {info['name']} - Market Cap: {info['market_cap']} - Sector: {info['sector']}")

    print("\nType 'n' for next page, 'p' for previous page, 'q' to quit browsing.")
    choice = input("Choose an option: ").lower()
    if choice == 'n' and page < total_pages:
        browse_stock_symbols(page + 1, page_size)
    elif choice == 'p' and page > 1:
        browse_stock_symbols(page - 1, page_size)
    elif choice == 'q':
        print("Exiting browsing.")
    else:
        print("Invalid choice, returning to the main menu.")

# ----------------------------- USER AUTHENTICATION -----------------------------

def load_users():
    if os.path.exists(USER_DATA_PATH):
        with open(USER_DATA_PATH, 'r') as file:
            return json.load(file)
    return {}

def save_users(users):
    with open(USER_DATA_PATH, 'w') as file:
        json.dump(users, file)

def register():
    users = load_users()
    username = input("Enter a new username: ")
    if username in users:
        print("Username already exists.")
        return None
    password = getpass.getpass("Enter a password: ")
    users[username] = {
        'password': password,
        'portfolio': {}
    }
    save_users(users)
    print(f"User {username} registered successfully!")
    return username

def login():
    users = load_users()
    username = input("Enter your username: ")
    if username not in users:
        print("No such user found.")
        return None
    password = getpass.getpass("Enter your password: ")
    if users[username]['password'] == password:
        print(f"Welcome back, {username}!")
        return username
    else:
        print("Incorrect password.")
        return None

# ----------------------------- STOCK FUNCTIONS -----------------------------

def get_stock_quote(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    try:
        data = stock.history(period="1d")
        if data.empty:
            return f"No data available for {ticker_symbol}"
        latest_data = data.iloc[-1]
        mark_stock_as_viewed(ticker_symbol)
        return {
            'Price': latest_data['Close'],
            'Daily High': latest_data['High'],
            'Daily Low': latest_data['Low'],
            'Volume': latest_data['Volume'],
            'Previous Close': stock.info.get('previousClose', 'N/A'),
            'Market Cap': stock.info.get('marketCap', 'N/A')
        }
    except Exception as e:
        return f"Error fetching data for {ticker_symbol}: {str(e)}"

def get_historical_data(ticker_symbol, start_date, end_date):
    stock = yf.Ticker(ticker_symbol)
    try:
        history = stock.history(start=start_date, end=end_date)
        return history
    except Exception as e:
        return f"Error fetching historical data for {ticker_symbol}: {str(e)}"

def get_fundamentals(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    try:
        fundamentals = {
            'Company Name': stock.info.get('longName', 'N/A'),
            'Sector': stock.info.get('sector', 'N/A'),
            'Income Statement': stock.financials.to_dict() if not stock.financials.empty else "No data",
            'Balance Sheet': stock.balance_sheet.to_dict() if not stock.balance_sheet.empty else "No data",
            'Cash Flow': stock.cashflow.to_dict() if not stock.cashflow.empty else "No data",
            'PE Ratio': stock.info.get('trailingPE', 'N/A'),
            'EPS': stock.info.get('trailingEps', 'N/A'),
            'Dividend Yield': stock.info.get('dividendYield', 'N/A'),
            'Market Cap': stock.info.get('marketCap', 'N/A'),
            '52 Week High': stock.info.get('fiftyTwoWeekHigh', 'N/A'),
            '52 Week Low': stock.info.get('fiftyTwoWeekLow', 'N/A'),
            'Beta': stock.info.get('beta', 'N/A'),
            'Last Dividend': stock.info.get('last_dividend_value', 'N/A'),
            'Recent Performance': {
                'Current Price': stock.info.get('currentPrice', 'N/A'),
                'Price Change': stock.info.get('regularMarketChangePercent', 'N/A'),
                'Volume': stock.info.get('volume', 'N/A')
            }
        }
        mark_stock_as_viewed(ticker_symbol)
        return fundamentals
    except Exception as e:
        return f"Error fetching fundamentals for {ticker_symbol}: {str(e)}"

def mark_stock_as_viewed(ticker):
    stock_cache = load_cache()
    if ticker in stock_cache:
        stock_cache[ticker]['viewed'] = True
        stock_cache[ticker]['timestamp'] = datetime.now().isoformat()
    save_cache(stock_cache)

# ----------------------------- PORTFOLIO MANAGEMENT -----------------------------

def track_portfolio(portfolio):
    total_value = 0
    for ticker_symbol, shares in portfolio.items():
        try:
            stock = yf.Ticker(ticker_symbol)
            price = stock.history(period="1d").iloc[-1]['Close']
            total_value += price * shares
        except Exception as e:
            print(f"Error fetching data for {ticker_symbol}: {str(e)}")
    return total_value

def add_to_portfolio(user, ticker_symbol, shares):
    users = load_users()
    if ticker_symbol not in users[user]['portfolio']:
        users[user]['portfolio'][ticker_symbol] = 0
    users[user]['portfolio'][ticker_symbol] += shares
    save_users(users)
    print(f"Added {shares} shares of {ticker_symbol} to your portfolio.")

def view_portfolio(user):
    users = load_users()
    portfolio = users[user]['portfolio']
    if not portfolio:
        print("Your portfolio is empty.")
        return
    total_value = track_portfolio(portfolio)
    print(f"Portfolio value: ${total_value:.2f}")
    for ticker_symbol, shares in portfolio.items():
        print(f"{ticker_symbol}: {shares} shares")

# ----------------------------- MENU SYSTEM -----------------------------

def main_menu(user):
    while True:
        print("\n--- Main Menu ---")
        print("1. View Stock Quotes: Get real-time stock prices and quotes.")
        print("2. Historical Data: Retrieve historical price data for analysis.")
        print("3. Fundamentals: Access detailed financial information about a stock.")
        print("4. Add to Portfolio: Add a stock to your investment portfolio.")
        print("5. View Portfolio: Review your current investments and their performance.")
        print("6. Browse Stock Symbols: Search for stock symbols and their details.")
        print("7. Save Information: Save your portfolio and stock information.")
        print("8. Log Out: Exit the application.")
        choice = input("Enter your choice: ")
        try:
            if choice == '1':
                ticker = input("Enter stock ticker: ")
                quote = get_stock_quote(ticker)
                print(f"Stock Quote for {ticker}: {quote}")
            elif choice == '2':
                ticker = input("Enter stock ticker: ")
                start_date = input("Enter start date (YYYY-MM-DD): ")
                end_date = input("Enter end date (YYYY-MM-DD): ")
                history = get_historical_data(ticker, start_date, end_date)
                print(f"Historical Data for {ticker}:\n{history}")
            elif choice == '3':
                ticker = input("Enter stock ticker: ")
                fundamentals = get_fundamentals(ticker)
                print(f"Fundamentals for {ticker}:\n{fundamentals}")
            elif choice == '4':
                ticker = input("Enter stock ticker: ")
                shares = int(input("Enter number of shares: "))
                add_to_portfolio(user, ticker, shares)
            elif choice == '5':
                view_portfolio(user)
            elif choice == '6':
                browse_stock_symbols()
            elif choice == '7':
                save_users(load_users())
                print("Information saved successfully.")
            elif choice == '8':
                print("Logging out...")
                break
            else:
                print("Invalid choice. Please try again.")
        except Exception as e:
            print(f"An error occurred: {str(e)}")

# ----------------------------- ENTRY POINT -----------------------------

def main():
    initialize_cache()
    cache_stocks()  # Cache stocks at startup
    while True:
        print("\n--- Welcome to the Stock CLI App ---")
        print("1. Register")
        print("2. Login")
        print("3. Exit")
        choice = input("Enter your choice: ")
        if choice == '1':
            user = register()
            if user:
                main_menu(user)
        elif choice == '2':
            user = login()
            if user:
                main_menu(user)
        elif choice == '3':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
