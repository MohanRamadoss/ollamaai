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

def get_historical_data(symbol: str) -> dict:
    """Get historical stock data for analysis"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1y")

        if hist.empty:
            return {"error": "No historical data available"}

        # Fix deprecation warnings by using iloc
        current_price = hist['Close'].iloc[-1]
        year_high = hist['High'].max()
        year_low = hist['Low'].min()
        avg_volume = hist['Volume'].mean()
        ma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        ma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]

        # Fix deprecation warning for initial price
        initial_price = hist['Close'].iloc[0]
        ytd_return = ((current_price - initial_price) / initial_price) * 100

        return {
            "year_high": year_high,
            "year_low": year_low,
            "avg_volume": avg_volume,
            "ma_50": ma_50,
            "ma_200": ma_200,
            "ytd_return": ytd_return,
            "error": False
        }
    except Exception as e:
        return {"error": f"Error fetching historical data: {str(e)}"}

def get_ai_analysis(stock_data: dict, model: str = 'mistral') -> str:
    """Get AI analysis using specified model"""
    if 'error' in stock_data:
        return "AI analysis unavailable due to error in stock data."

    historical = get_historical_data(stock_data['symbol'])
    historical_text = "Historical data unavailable." if historical.get("error") else f"""
Historical Analysis:
• 52-Week High: ${historical['year_high']:.2f}
• 52-Week Low: ${historical['year_low']:.2f}
• 50-Day MA: ${historical['ma_50']:.2f}
• 200-Day MA: ${historical['ma_200']:.2f}
• YTD Return: {historical['ytd_return']:.2f}%
• Average Volume: {historical['avg_volume']:,.0f}
"""

    prompt = f"""
    As a financial analyst, analyze this stock:

    Current Data:
    Company: {stock_data['company_name']} ({stock_data['symbol']})
    Price: {stock_data['currency']} {stock_data['price']}
    Change: {stock_data['change_percent']}%
    Volume: {stock_data['volume']}
    Market Cap: {stock_data['market_cap']}
    Sector: {stock_data['sector']}
    Industry: {stock_data['industry']}

    {historical_text}

    Provide:
    1. Technical Analysis
    2. Market Position
    3. Risk Assessment
    4. Short-term Outlook

    Keep it concise and factual.
    """

    try:
        response = ollama.chat(model=model, messages=[
            {
                'role': 'user',
                'content': prompt
            }
        ])
        return f"\n🤖 AI Analysis (using {model}):\n{response.message.content}"
    except Exception as e:
        return f"\n❌ AI Analysis unavailable: {str(e)}"

def format_stock_output(stock_data: dict, model: str = 'mistral') -> str:
    """Format stock information for display"""
    if 'error' in stock_data:
        return f"❌ {stock_data['message']}"

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
    return basic_info + get_ai_analysis(stock_data, model)

def get_stock_info():
    """Interactive function to get stock information"""
    AI_MODELS = {
        '1': ('mistral', 'Balanced analysis'),
        '2': ('llama3.1', 'Advanced analysis'),
        '3': ('llama3.2', 'Efficient analysis')
    }

    while True:
        print("\n=== AI-Powered Stock Analyzer ===")
        print("\nAvailable AI Models:")
        for key, (model, desc) in AI_MODELS.items():
            print(f"{key}. {model} - {desc}")

        model_choice = input("\nSelect model (1-3) [default=1]: ").strip() or '1'
        selected_model, _ = AI_MODELS.get(model_choice, AI_MODELS['1'])

        print("\nEnter a stock symbol (or 'quit' to exit)")
        symbol = input("Stock symbol: ").strip().upper()

        if symbol.lower() == 'quit':
            print("Thank you for using AI-Powered Stock Analyzer!")
            break

        if symbol:
            print(f"\n🔍 Fetching data and generating {selected_model} analysis...")
            result = get_stock_price(symbol)
            print(format_stock_output(result, selected_model))

        print("\nPopular symbols:")
        print("AAPL (Apple)   GOOGL (Google)   MSFT (Microsoft)")
        print("AMZN (Amazon)  TSLA (Tesla)     META (Meta/Facebook)")

        continue_check = input("\nAnalyze another stock? (y/n): ").lower()
        if continue_check != 'y':
            print("Thank you for using AI-Powered Stock Analyzer!")
            break

if __name__ == "__main__":
    get_stock_info()