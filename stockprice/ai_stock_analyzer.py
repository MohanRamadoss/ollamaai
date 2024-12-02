import ollama
import yfinance as yf
from typing import Dict, Any, Callable
from datetime import datetime
import json

def get_stock_price(symbol: str) -> dict:
    """Get stock price and additional information with error handling"""
    try:
        ticker = yf.Ticker(symbol)
        price_attrs = ['regularMarketPrice', 'currentPrice', 'price']

        # Get price
        price = None
        for attr in price_attrs:
            if attr in ticker.info and ticker.info[attr] is not None:
                price = ticker.info[attr]
                break

        if price is None:
            fast_info = ticker.fast_info
            if hasattr(fast_info, 'last_price') and fast_info.last_price is not None:
                price = fast_info.last_price

        if price is None:
            raise Exception("No valid price data found")

        # Get additional info
        info = {
            'symbol': symbol.upper(),
            'price': price,
            'currency': ticker.info.get('currency', 'USD'),
            'company_name': ticker.info.get('longName', 'Unknown'),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'change_percent': ticker.info.get('regularMarketChangePercent', 0),
            'volume': ticker.info.get('volume', 'N/A'),
            'market_cap': ticker.info.get('marketCap', 'N/A'),
            'sector': ticker.info.get('sector', 'Unknown'),
            'industry': ticker.info.get('industry', 'Unknown'),
            'pe_ratio': ticker.info.get('trailingPE', 'N/A'),
        }
        return info

    except Exception as e:
        return {
            'error': True,
            'message': f"Error fetching data for {symbol}: {str(e)}",
            'symbol': symbol.upper()
        }

def get_ai_analysis(stock_data: dict) -> str:
    """Get AI analysis of stock data using Ollama"""
    if 'error' in stock_data:
        return "AI analysis unavailable due to error in stock data."

    prompt = f"""
    As a financial analyst, provide a brief analysis of this stock:
    Company: {stock_data['company_name']} ({stock_data['symbol']})
    Current Price: {stock_data['currency']} {stock_data['price']}
    Change: {stock_data['change_percent']}%
    Volume: {stock_data['volume']}
    Market Cap: {stock_data['market_cap']}
    Sector: {stock_data['sector']}
    Industry: {stock_data['industry']}
    P/E Ratio: {stock_data['pe_ratio']}

    Please provide:
    1. A brief market position analysis
    2. Key performance indicators
    3. Potential risk factors
    Keep it concise and factual.
    """

    try:
        response = ollama.chat(model='mistral', messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ])
        return f"\n🤖 AI Analysis:\n{response.message.content}"
    except Exception as e:
        return f"\n❌ AI Analysis unavailable: {str(e)}"

def format_stock_output(stock_data: dict) -> str:
    """Format stock information for display"""
    if 'error' in stock_data:
        return f"❌ {stock_data['message']}"

    # Format market cap in billions
    market_cap = stock_data['market_cap']
    if isinstance(market_cap, (int, float)):
        market_cap = f"${market_cap/1e9:.2f}B"

    basic_info = f"""
📈 Stock Information for {stock_data['company_name']} ({stock_data['symbol']})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Current Price: {stock_data['currency']} {stock_data['price']:.2f}
• Change: {stock_data['change_percent']:.2f}%
• Volume: {stock_data['volume']:,}
• Market Cap: {market_cap}
• Sector: {stock_data['sector']}
• Industry: {stock_data['industry']}
• P/E Ratio: {stock_data['pe_ratio']}
• Last Updated: {stock_data['timestamp']}
"""
    # Get AI analysis
    ai_analysis = get_ai_analysis(stock_data)

    return basic_info + ai_analysis

def get_stock_info():
    """Interactive function to get stock information"""
    while True:
        print("\n=== AI-Powered Stock Analyzer ===")
        print("Enter a stock symbol (or 'quit' to exit)")
        symbol = input("Stock symbol: ").strip().upper()

        if symbol.lower() == 'quit':
            print("Thank you for using AI-Powered Stock Analyzer!")
            break

        if symbol:
            print("\n🔍 Fetching data and generating AI analysis...")
            result = get_stock_price(symbol)
            print(format_stock_output(result))

        print("\nPopular symbols:")
        print("AAPL (Apple)   GOOGL (Google)   MSFT (Microsoft)")
        print("AMZN (Amazon)  TSLA (Tesla)     META (Meta/Facebook)")

        continue_check = input("\nAnalyze another stock? (y/n): ").lower()
        if continue_check != 'y':
            print("Thank you for using AI-Powered Stock Analyzer!")
            break

if __name__ == "__main__":
    get_stock_info()