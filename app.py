import yfinance as yf
import json
import os
import getpass

# Paths for storing user data
USER_DATA_PATH = 'users.json'

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
    data = stock.history(period="1d").iloc[0]
    return {
        'Price': data['Close'],
        'Daily High': data['High'],
        'Daily Low': data['Low'],
        'Volume': data['Volume'],
        'Previous Close': stock.info['previousClose'],
        'Market Cap': stock.info.get('marketCap', 'N/A')
    }

def get_historical_data(ticker_symbol, start_date, end_date):
    stock = yf.Ticker(ticker_symbol)
    history = stock.history(start=start_date, end=end_date)
    return history

def get_fundamentals(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    return {
        'Income Statement': stock.financials,
        'Balance Sheet': stock.balance_sheet,
        'Cash Flow': stock.cashflow,
        'PE Ratio': stock.info.get('trailingPE', 'N/A'),
        'EPS': stock.info.get('trailingEps', 'N/A'),
        'Dividend Yield': stock.info.get('dividendYield', 'N/A'),
        'Market Cap': stock.info.get('marketCap', 'N/A')
    }

# ----------------------------- PORTFOLIO MANAGEMENT -----------------------------

def track_portfolio(portfolio):
    total_value = 0
    for ticker_symbol, shares in portfolio.items():
        stock = yf.Ticker(ticker_symbol)
        price = stock.history(period="1d").iloc[0]['Close']
        total_value += price * shares
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
    print(f"Portfolio value: ${total_value}")
    for ticker_symbol, shares in portfolio.items():
        print(f"{ticker_symbol}: {shares} shares")
    
# ----------------------------- MENU SYSTEM -----------------------------

def main_menu(user):
    while True:
        print("\n--- Main Menu ---")
        print("1. View Stock Quotes")
        print("2. Historical Data")
        print("3. Fundamentals")
        print("4. Add to Portfolio")
        print("5. View Portfolio")
        print("6. Save Information")
        print("7. Log Out")
        
        choice = input("Enter your choice: ")
        
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
            save_users(load_users())  # Ensures user data is saved
            print("Information saved successfully.")
        
        elif choice == '7':
            print("Logging out...")
            break
        
        else:
            print("Invalid choice. Please try again.")

# ----------------------------- ENTRY POINT -----------------------------

def main():
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
