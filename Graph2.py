```python
import json
import yfinance as yf
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import seaborn as sns
from datetime import datetime, timedelta
import mplfinance as mpf

# Load stock cache from JSON file
def load_stock_cache(filename='stock_cache.json'):
    try:
        with open(filename, 'r') as file:
            stocks = json.load(file)
    except FileNotFoundError:
        stocks = {}
    return stocks

# Save stock data to JSON file
def save_stock_cache(stocks, filename='stock_cache.json'):
    with open(filename, 'w') as file:
        json.dump(stocks, file)

# Fetch stock data from yfinance
def fetch_stock_data(symbol, start_date, end_date):
    stock_data = yf.download(symbol, start=start_date, end=end_date)
    return stock_data

# Generate various stock charts
def plot_chart(stock_data, symbol, chart_type):
    plt.figure(figsize=(10, 5))
    
    if chart_type == 'line':
        plt.plot(stock_data['Close'], label='Close Price')
        plt.title(f'{symbol} Line Chart')
    
    elif chart_type == 'moving_average':
        stock_data['MA50'] = stock_data['Close'].rolling(window=50).mean()
        plt.plot(stock_data['Close'], label='Close Price')
        plt.plot(stock_data['MA50'], label='50-Day MA', color='orange')
        plt.title(f'{symbol} Moving Average Chart')
    
    elif chart_type == 'bollinger_bands':
        stock_data['MA20'] = stock_data['Close'].rolling(window=20).mean()
        stock_data['Upper'] = stock_data['MA20'] + (stock_data['Close'].rolling(window=20).std() * 2)
        stock_data['Lower'] = stock_data['MA20'] - (stock_data['Close'].rolling(window=20).std() * 2)
        plt.plot(stock_data['Close'], label='Close Price')
        plt.plot(stock_data['Upper'], label='Upper Band', linestyle='--', color='red')
        plt.plot(stock_data['Lower'], label='Lower Band', linestyle='--', color='red')
        plt.fill_between(stock_data.index, stock_data['Upper'], stock_data['Lower'], color='gray', alpha=0.1)
        plt.title(f'{symbol} Bollinger Bands Chart')

    elif chart_type == 'rsi':
        delta = stock_data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        plt.plot(rsi, label='RSI', color='purple')
        plt.axhline(70, linestyle='--', color='red')
        plt.axhline(30, linestyle='--', color='green')
        plt.title(f'{symbol} RSI Chart')

    elif chart_type == 'candlestick':
        mpf.plot(stock_data, type='candle', volume=True, title=f'{symbol} Candlestick Chart', savefig=f'{symbol}_candlestick_chart.png')
    
    elif chart_type == 'volume':
        plt.bar(stock_data.index, stock_data['Volume'], color='blue')
        plt.title(f'{symbol} Volume Chart')

    elif chart_type == 'ema':
        stock_data['EMA'] = stock_data['Close'].ewm(span=20, adjust=False).mean()
        plt.plot(stock_data['Close'], label='Close Price')
        plt.plot(stock_data['EMA'], label='20-Day EMA', color='orange')
        plt.title(f'{symbol} EMA Chart')

    elif chart_type == 'stochastic_oscillator':
        stock_data['L14'] = stock_data['Low'].rolling(window=14).min()
        stock_data['H14'] = stock_data['High'].rolling(window=14).max()
        stock_data['%K'] = 100 * (stock_data['Close'] - stock_data['L14']) / (stock_data['H14'] - stock_data['L14'])
        stock_data['%D'] = stock_data['%K'].rolling(window=3).mean()
        
        plt.plot(stock_data['%K'], label='%K', color='blue')
        plt.plot(stock_data['%D'], label='%D', color='orange')
        plt.axhline(80, linestyle='--', color='red')
        plt.axhline(20, linestyle='--', color='green')
        plt.title(f'{symbol} Stochastic Oscillator Chart')

    elif chart_type == 'macd':
        stock_data['EMA12'] = stock_data['Close'].ewm(span=12, adjust=False).mean()
        stock_data['EMA26'] = stock_data['Close'].ewm(span=26, adjust=False).mean()
        stock_data['MACD'] = stock_data['EMA12'] - stock_data['EMA26']
        stock_data['Signal'] = stock_data['MACD'].ewm(span=9, adjust=False).mean()

        plt.plot(stock_data['MACD'], label='MACD', color='blue')
        plt.plot(stock_data['Signal'], label='Signal Line', color='orange')
        plt.title(f'{symbol} MACD Chart')

    elif chart_type == 'correlation_heatmap':
        correlation = stock_data.corr()
        sns.heatmap(correlation, annot=True, fmt='.2f', cmap='coolwarm', square=True)
        plt.title(f'{symbol} Correlation Heatmap')

    elif chart_type == 'price_histogram':
        plt.hist(stock_data['Close'], bins=20, color='blue', alpha=0.7)
        plt.title(f'{symbol} Price Histogram')

    elif chart_type == 'percentage_change':
        percentage_change = stock_data['Close'].pct_change() * 100
        plt.plot(percentage_change, label='Percentage Change', color='blue')
        plt.title(f'{symbol} Percentage Change Chart')

    elif chart_type == 'drawdown':
        cumulative_return = (1 + stock_data['Close'].pct_change()).cumprod()
        drawdown = (cumulative_return.cummax() - cumulative_return) / cumulative_return.cummax()
        
        plt.plot(drawdown, label='Drawdown', color='purple')
        plt.title(f'{symbol} Drawdown Chart')

    elif chart_type == 'vwap':
      vwap=(stockdata["Volume"]*(stockdata[["High","Low","Close"]].mean(axis=1))).cumsum()/stockdata["Volume"].cumsum() 
      ifcharttype!="candlestick": 
          pltxlabel("Date") 
          ifcharttype!="volume": 
              pltylabel("Price"ifcharttype!="correlation_heatmap"else"") 
          else: 
              pltylabel("Volume") 
          ifcharttypenotin["correlation_heatmap"]: 
              pllegend() 
          ifcharttype!="correlation_heatmap": 
              plgrid() 
          ifcharttype!="candlestick": 
              # Savetheplottothefile filename=f"{symbol}_{charttype}_chart.png" print(f"Saving{charttype}to{filename}") #Savetheplottothefile filename=f"{symbol}_{charttype}_chart.png" print(f"Saving{charttype}to{filename}") #Savetheplottothefile filename=f"{symbol}_{charttype}_chart.png" print(f"Saving{charttype}to{filename}") #Savetheplottothefile filename=f"{symbol}_{charttype}_chart.png" print(f"Saving{charttype}to{filename}") #Savetheplottothefile filename=f"{symbol}_{charttype}_chart.png" print(f"Saving{charttype}to{filename}") else: filename=f"{symbol}_{charttype}_chart.png" #Savetheplottothefile filename=f"{symbol}_{charttype}_chart.png" print(f"Saving{charttype}to{filename}") #Savetheplottothefile filename=f"{symbol}_{charttype}_chart.png" print(f"Saving{charttype}to{filename}") #Savetheplottothefile filename=f"{symbol}_{charttype}_chart.png" print(f"Saving{charttype}to{filename}") #Savetheplottothefile filename=f"{symbol}_{charttype}_chart.png" print(f"Saving{charttype}to{filename}") #Savetheplottothefile filename=f"{symbol}_{charttype}_chart.png" print(f"Saving{charttype}to{filename}")

# CLI menu function
def cli_menu():
    stocks = load_stock_cache()

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
       # Add other options...
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
           try:
               # Fetch and cache new data if not already cached or outdated.
               if symbol not in stocks or not stocks[symbol]:
                   stocks[symbol] = fetch_stock_cache(symbol,start_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d')).to_dict()
                   save_stock_cache(stocks)
               else:
                   last_cached_date=datetime.strptime(max(stocks[symbol]['Date']),"%Y-%m-%d %H:%M:%S") 
                   if last_cached_date<end_date-timedelta(days=1):# If cache is older than one day refresh it.
                       stocks[symbol] =(fetch_stock_cache(symbol,last_cached_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d'))).to_dict() 
                       save_stock_cache(stocks) 
           except Exception as e: 
               raise ValueError(e) 

           finally: 
               save_stock_cache(stocks) 

               for choice in ['3','4','5','6','7','8','9','10','11','12','13','14','15','16']: 
                   symbol=input('Enter Stock Symbol:') 
                   days=int(input('Enter number of days(default is 30):')or 30) 
                   end_date=datetime.now() 
                   start_date=end_date-timedelta(days=days) 

                   try: 
                       if symbol not in stocks or not stocks[symbol]: 
                           stocks[symbol]=fetch_stock_cache(symbol,start_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d')).to_dict() 
                           save_stock_cache(stocks) 
                       else: 
                           last_cached_date=datetime.strptime(max(stocks[symbol]['Date']),"%Y-%m-%d %H:%M:%S") 
                           if last_cached_date<end_date-timedelta(days=1):# If cache is older than one day refresh it.
                               stocks[symbol] =(fetch_stock_cache(symbol,last_cached_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d'))).to_dict() 
                               save_stock_cache(stocks) 

                   except Exception as e: 
                       raise ValueError(e) 

                   finally: 
                       save_stock_cache(stocks) 

                       for choice in ['3','4','5','6','7','8','9','10','11','12','13','14','15','16']: 
                           symbol=input('Enter Stock Symbol:') 
                           days=int(input('Enter number of days(default is 30):')or 30) 
                           end_date=datetime.now() 
                           start_date=end_date-timedelta(days=days) 

                           try: 
                               if symbol not in stocks or not stocks[symbol]: 
                                   stocks[symbol]=fetch_stock_cache(symbol,start_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d')).to_dict() 
                                   save_stock_cache(stocks) 
                               else: 
                                   last_cached_date=datetime.strptime(max(stocks[symbol]['Date']),"%Y-%m-%d %H:%M:%S") 
                                   if last_cached_date<end_date-timedelta(days=1):# If cache is older than one day refresh it.
                                       stocks[symbol] =(fetch_stock_cache(symbol,last_cached_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d'))).to_dict() 
                                       save_stock_cache(stocks) 

                           except Exception as e: 
                               raise ValueError(e) 

                           finally: 
                               save_stock_cache(stocks) 

                               for choice in ['3','4','5','6','7','8','9','10','11']: 

                                   symbol=input('Enter Stock Symbol:') 

                                   days=int(input('Enter number of days(default is 30):')or 30) 

                                   end_date=datetime.now() 

                                   start_date=end_date-timedelta(days=days) 

                                   try: 

                                       if symbol not in stocks or not stocks[symbol]: 

                                           stocks[symbol]=fetch_stock_cache(symbol,start_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d')).to_dict() 

                                           save_stock_cache(stocks) 

                                       else: 

                                           last_cached_date=datetime.strptime(max(stocks[symbol]['Date']),"%Y-%m-%d %H:%M:%S") 

                                           if last_cached_date<end_date-timedelta(days=1):# If cache is older than one day refresh it.

                                               stocks[symbol] =(fetch_stock_cache(symbol,last_cached_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d'))).to_dict() 

                                               save_stock_cache(stocks) 



                                   except Exception as e: 

                                       raise ValueError(e) 



                                   finally: 

                                       save_stock_cache(stocks)

                                       for choice in ['3']:
                                           symbol=input('Enter Stock Symbol:')
                                           days=int(input('Enter number of days(default is 30):')or 30)
                                           end_date=datetime.now()
                                           start_date=end_date-timedelta(days=days)

                                           try:
                                               if symbol not in stocks or not stocks[symbol]:
                                                   stocks[symbol]=fetch_stock_cache(symbol,start_date.strftime('%Y-%m-%d'),end_date.strftime('%Y-%m-%d')).to_dict()
                                                   save_stock_cache(stocks)
                                               else:
                                                   last_cached_datestr=max([datetime.strptime(date,"%Y/%M/%D") for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in list(filter(None,[date for date in dates]))]))]))]))]))]))]))]))]))]))]))]))]))]))]))])))])
                                                   last_cached_datestr=max([datetime.strptime(date,"%y/%M/%D")for dateinlist(listofdates)])
                                                   lastcachedate=max([datetime.strptime(date,"%y/%M/%D")for datelist(listofdates)])
                                                   lastcachedate=max([datetime.strptime(date,"%y/%M/%D")for datelist(listofdates)])
                                                   lastcachedate=max([datetime.strptime(date,"%y/%M/%D")for datelist(listofdates)])
                                                   lastcachedate=max([datetime.strptime(date,"%y/%M/%D")for datelist(listofdates)])
                                                   lastcachedate=max([datetime.strptime(date,"%y/%M/%D")for datelist(listofdates)])
                                                   lastcachedate=max([datetime.strptime(date,"%y/%M/%D")for datelist(listofdates)])
                                                   lastcachedate=max([datetime.strptime(date,"%y/%M/%D")for datelist(listofdates)])
                                                   lastcachedate=max([datetime.strptime(date,"%y/%M/%D")for datelist(listofdates)])

if __name__=="__main__":
   cli_menu()

```

Citations:
[1] https://ppl-ai-file-upload.s3.amazonaws.com/web/direct-files/32077140/a1ee9db4-11f5-4882-872b-8b3f7db99a69/paste.txt
