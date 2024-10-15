
# **Stock Information CLI App**

The Stock Information CLI App is a command-line interface (CLI) application that allows users to register, log in, and access a wide range of stock data via the `yfinance` library. Users can view real-time stock quotes, check historical data, analyze fundamentals, manage portfolios, and set alerts. The app also allows saving and loading of user data for persistence across sessions.

<details>
   <summary>
[Stock exchanges are centralized marketplaces where securities, such as stocks, bonds, and other financial instruments, are bought and sold. They play a crucial role in the functioning of the financial markets, facilitating the trading of securities and providing a platform for companies to raise capital by issuing shares. Here’s an overview of their key features and functions]
      <details>
      (Exchanges.md)


## **Table of Contents**

1. [Features](#features)
2. [Installation](#installation)
3. [Usage](#usage)
4. [CLI Navigation and Menus](#cli-navigation-and-menus)
5. [User Authentication](#user-authentication)
6. [Stock Features](#stock-features)
7. [Portfolio Management](#portfolio-management)
8. [Saving and Loading Data](#saving-and-loading-data)
9. [File Structure](#file-structure)
10. [Contributing](#contributing)
11. [Changelog](#changelog)

---

## **Features**

- **User Authentication**: Register, log in, and save your data (portfolio, settings) across sessions.
- **Stock Quotes**: Get real-time stock prices, daily highs/lows, volume, and market cap.
- **Historical Data**: Retrieve stock historical data for customizable time periods.
- **Fundamental Analysis**: View financial data, including income statements, balance sheets, cash flows, P/E ratios, and more.
- **Portfolio Management**: Add stocks to a personalized portfolio, view its value, and track performance.
- **Data Persistence**: Save user information, portfolio data, and other settings.
- **Alerts**: Set alerts based on stock price targets (planned feature).

---

## **Installation**

To set up the CLI app, follow these steps:

1. **Clone the repository**:
   ```bash
   git clone https://github.com/unaveragetech/Infobroker.git
   cd stock-cli-app
   ```

2. **Install the required dependencies**:
   Install the Python dependencies using `pip` and the provided `requirements.txt` file:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   To start the CLI app, run the main Python file:
   ```bash
   python tick.py-->python app.py
   ```

---

## **Usage**

### **First-Time Setup**

- **Register**: When you first run the app, you'll need to create a user profile. This involves choosing a username and a password.
- **Login**: Once you have registered, you can log in with your credentials.

### **General Navigation**
- Use the numbered menu to navigate the app.
- Press the corresponding number to select a feature (e.g., "1" for **View Stock Quotes**).
- You can log out or save data at any time by choosing the appropriate menu options.

---

## **CLI Navigation and Menus**

Once logged in, you'll be greeted with a **Main Menu**. Here's the basic structure of the menus:

### **Main Menu**:
```
--- Main Menu ---
1. View Stock Quotes
2. Historical Data
3. Fundamentals
4. Add to Portfolio
5. View Portfolio
6. Save Information
7. Log Out
```

- **View Stock Quotes**: Fetch and display real-time stock data for a specific ticker symbol.
- **Historical Data**: Get historical data for a stock (daily, weekly, etc.).
- **Fundamentals**: View key financial data (P/E ratio, market cap, etc.).
- **Add to Portfolio**: Add stocks and the number of shares to your portfolio.
- **View Portfolio**: See the current value of your portfolio and stock holdings.
- **Save Information**: Save your portfolio and settings to disk for later use.
- **Log Out**: Safely exit the application and return to the login screen.

---

## **User Authentication**

### **Registering a New User**

1. Upon first starting the application, select **1. Register**.
2. Enter your desired username and password.
3. Registration is successful, and the application will log you in automatically.

### **Logging In**

1. From the home screen, select **2. Login**.
2. Enter your registered username and password.
3. If successful, you'll be redirected to the **Main Menu**.

---

## **Stock Features**

Once logged in, you can access the stock-related features in the **Main Menu**.

### **1. View Stock Quotes**

To view real-time stock data:
1. Select **1. View Stock Quotes** from the main menu.
2. Enter the ticker symbol of the stock (e.g., `AAPL` for Apple).
3. The application will display:
   - Stock Price
   - Daily High and Low
   - Trading Volume
   - Market Cap
   - Previous Close

### **2. Historical Data**

To view the historical data of a stock:
1. Select **2. Historical Data** from the main menu.
2. Enter the stock ticker, start date, and end date.
3. The historical data (Open, High, Low, Close) will be displayed for the specified date range.

### **3. Fundamentals**

To view fundamental analysis data:
1. Select **3. Fundamentals** from the main menu.
2. Enter the stock ticker.
3. The following data will be displayed:
   - P/E Ratio
   - EPS (Earnings per Share)
   - Dividend Yield
   - Market Cap
   - Financial statements (Income, Balance Sheet, and Cash Flow)

---

## **Portfolio Management**

### **4. Add to Portfolio**

To add stocks to your portfolio:
1. Select **4. Add to Portfolio** from the main menu.
2. Enter the stock ticker and the number of shares.
3. The stock will be added to your portfolio, which will be updated on the **View Portfolio** screen.

### **5. View Portfolio**

To view your current portfolio:
1. Select **5. View Portfolio** from the main menu.
2. The current value of your portfolio will be displayed along with the stocks and the number of shares held.

---

## **Saving and Loading Data**

### **6. Save Information**

- The app automatically saves user data (e.g., portfolio, preferences) when exiting, but you can manually save at any time by selecting **6. Save Information** from the main menu.
- The user data is stored in the `users.json` file, which holds:
  - Usernames and passwords (in plain text – consider adding encryption in future versions).
  - Portfolio data and user settings.

---

## **File Structure**

- **`main.py`**: The entry point for the application.
- **`users.json`**: Stores user data including authentication and portfolio information.
- **`requirements.txt`**: List of required Python dependencies.

---

## **Contributing**

We welcome contributions to improve the app! Here’s how you can contribute:

1. Fork the repository.
2. Create a new feature branch.
3. Commit your changes.
4. Push the branch to your fork.
5. Open a pull request, and provide a detailed description of the changes.

---

## **Command Reference**

Here’s a list of all the commands you’ll need to run the program from start to finish.

| **Command**                           | **Description**                                                                                 |
|---------------------------------------|-------------------------------------------------------------------------------------------------|
| `git clone https://github.com/unaveragetech/Infobroker.git` | Clones the project repository to your local machine.                                |
| `cd stock-stockbroker`                    | Changes directory to the project folder.                                                        |
| `pip install -r requirements.txt`     | Installs the Python dependencies (yfinance, pandas).                                             |
| `python tick.py-->python app.py`                      | Starts the CLI application.                                                                     |
| **In-Application Commands**:          | **Once inside the app, use the following options**:                                              |
| `1`                                   | Register a new user.                                                                            |
| `2`                                   | Log in as an existing user.                                                                     |
| `3`                                   | Exit the application.                                                                           |
| **Main Menu Commands**:               | **Once logged in, use these commands to interact with the app**:                                 |
| `1`                                   | View real-time stock quotes by entering a ticker symbol (e.g., `AAPL`).                          |
| `2`                                   | View historical data of a stock by entering the ticker symbol and a date range.                  |
| `3`                                   | View fundamental analysis of a stock by entering the ticker symbol (e.g., P/E ratio, Market Cap).|
| `4`                                   | Add stocks to your portfolio by entering a ticker symbol and number of shares.                   |
| `5`                                   | View your portfolio’s total value and holdings.                                                  |
| `6`                                   | Save your information (user data and portfolio) to disk.                                         |
| `7`                                   | Log out from your session.                                                                      |

---

## **Code Explanation Examples**

This table contains explanations for key parts of the code. Use it to better understand how the app is structured and operates.

| **Code Snippet**                                           | **Explanation**                                                                                                     |
|------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| `load_users()`                                              | Loads all users from the `users.json` file. Returns an empty dictionary if the file doesn't exist.                   |
| `save_users(users)`                                         | Saves the current list of users to the `users.json` file. Updates user portfolios, authentication, and preferences.  |
| `register()`                                                | Handles user registration by asking for a username and password. Saves this information to the `users.json` file.    |
| `login()`                                                   | Handles user login by verifying the username and password from `users.json`. Grants access to the main menu if valid.|
| `get_stock_quote(ticker_symbol)`                            | Fetches the real-time stock price, daily highs, lows, and volume using `yfinance` for a given ticker symbol.         |
| `get_historical_data(ticker_symbol, start_date, end_date)`  | Retrieves historical data (open, high, low, close, etc.) for a given stock between two dates using `yfinance`.       |
| `get_fundamentals(ticker_symbol)`                           | Extracts financial data, such as the P/E ratio, market cap, and income statement from `yfinance`.                    |
| `track_portfolio(portfolio)`                                | Calculates the total value of a user's portfolio by fetching the latest stock prices and multiplying by share count.  |
| `add_to_portfolio(user, ticker_symbol, shares)`             | Adds stocks to the user's portfolio by appending the ticker symbol and number of shares. Saves the portfolio to disk. |
| `view_portfolio(user)`                                      | Displays the user's portfolio, showing stock holdings, number of shares, and the current portfolio value.            |
| `save_users(load_users())`                                  | Ensures that all user data, including portfolios, are saved to the `users.json` file when requested.                 |
| `main_menu(user)`                                           | The primary menu that users interact with after logging in. Handles navigation between stock-related features.       |
| `if __name__ == "__main__": main()`                         | The entry point of the application, which ensures the app runs only when executed directly as a script.              |

---


---

## Ticker Generation Functions

This project includes several functions for generating random ticker symbols based on specified criteria. Below is a summary of the available functions:

### Functions Overview

| **Function Name**                     | **Description**                                                                                                 | **Example Use Case**                                                                 |
|---------------------------------------|-------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| `generate_us_stock_ticker`           | Generates a random ticker for US stock exchanges with optional suffixes like `NYSE`, `NASDAQ`, and `US`.       | For general US stocks (e.g., `AAPL`, `GOOG`).                                      |
| `generate_eu_stock_ticker`           | Generates a random ticker for European stock exchanges, using suffixes for specific exchanges like `.LSE`, `.FR`. | For European stocks (e.g., `HSBA.LSE`, `BNP.FR`).                                  |
| `generate_tech_stock_ticker`         | Generates ticker symbols for technology companies, usually 2-4 characters.                                    | Suitable for tech companies listed on US or global markets (e.g., `MSFT`, `GOOG`). |
| `generate_bond_ticker`                | Generates ticker symbols for bonds or fixed-income securities, using `.BOND` as a suffix.                      | For bond markets (e.g., `T10Y.BOND`).                                              |
| `generate_crypto_ticker`              | Generates ticker symbols for cryptocurrencies, usually 3-5 characters.                                         | For cryptocurrency tickers (e.g., `BTC`, `ETH`).                                  |
| `generate_health_stock_ticker`        | Generates ticker symbols for healthcare companies, commonly using 3-5 characters.                           | For healthcare stocks (e.g., `PFE`, `JNJ`).                                        |
| `generate_luxury_brand_ticker`        | Generates tickers for luxury goods companies, allowing for longer names and global exchanges like `.FR`, `.IT`. | For luxury brands listed on international markets (e.g., `LVMH.FR`).               |
| `generate_energy_stock_ticker`        | Generates ticker symbols for energy companies, typically 3-5 characters, with suffix options like `.OIL`, `.GAS`. | For energy sector stocks (e.g., `XOM.OIL`, `BP.GAS`).                             |
| `generate_fintech_stock_ticker`      | Generates ticker symbols for fintech companies, typically 4-5 characters.                                    | For fintech stocks (e.g., `PYPL`, `SQ`).                                           |

### Example Function Code

Here’s an example of how you might define one of these functions in the Tick.py around line "60" :

```python
def generate_us_stock_ticker(min_length=1, max_length=4, prefix='', suffix='US', 
                              exclude_tickers=None, allowed_suffixes=['US', 'NYSE', 'NASDAQ']):
    return generate_random_ticker(min_length, max_length, prefix, suffix, 
                                   exclude_tickers, allowed_suffixes=allowed_suffixes)
```

### Usage

You can call these functions to generate random ticker symbols based on your criteria. This feature can be particularly useful for testing, simulations, or demonstrations.

---
## **Installation**

Follow the [Installation](#installation) instructions above to set up the app, and use the command reference table to navigate the program efficiently.

---
## **Changelog**

### **Version 1.0.0**
- Initial release of the Stock CLI App.
- Features include:
  - User registration and login system.
  - Stock quotes, historical data, and fundamentals.
  - Portfolio management and data persistence.

