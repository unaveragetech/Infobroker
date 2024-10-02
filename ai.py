import json
import csv
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import time
import random

def check_stock_symbol_yf(symbol):
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        if 'symbol' in info:
            return f"Valid symbol. Company: {info.get('longName', 'N/A')}"
        else:
            return "Not a valid symbol"
    except Exception as e:
        return f"Error checking symbol: {str(e)}"

def query_google(stock_symbol):
    url = f"https://www.google.com/search?q={stock_symbol}+stock"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        result = soup.find('div', class_='BNeawe s3v9rd AP7Wnd')
        return result.text if result else "No information found on Google"
    except Exception as e:
        return f"Error querying Google: {str(e)}"

def query_bing(stock_symbol):
    url = f"https://www.bing.com/search?q={stock_symbol}+stock"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        result = soup.find('div', class_='b_snippet')
        return result.text if result else "No information found on Bing"
    except Exception as e:
        return f"Error querying Bing: {str(e)}"

# Read the JSON file
with open('incomplete_tickers.json', 'r') as file:
    data = json.load(file)

# Create and write to CSV file
with open('stock_symbols_check.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Symbol', 'Yahoo Finance Status', 'Google Response', 'Bing Response'])  # Write header

    for symbol in data.keys():
        print(f"Checking symbol: {symbol}")
        yf_response = check_stock_symbol_yf(symbol)
        google_response = query_google(symbol)
        bing_response = query_bing(symbol)
        writer.writerow([symbol, yf_response, google_response, bing_response])
        
        # Add a random delay between requests
        time.sleep(random.uniform(5, 15))

print("CSV file has been created: stock_symbols_check.csv")