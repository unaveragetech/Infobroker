
# **Stock Information CLI App**

The Stock Information CLI App is a command-line interface (CLI) application that allows users to register, log in, and access a wide range of stock data via the `yfinance` library. Users can view real-time stock quotes, check historical data, analyze fundamentals, manage portfolios, and set alerts. The app also allows saving and loading of user data for persistence across sessions.

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
   git clone https://github.com/your-repo/stock-cli-app.git
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
   python main.py
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

## **Changelog**

### **Version 1.0.0**
- Initial release of the Stock CLI App.
- Features include:
  - User registration and login system.
  - Stock quotes, historical data, and fundamentals.
  - Portfolio management and data persistence.

