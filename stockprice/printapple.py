import ollama
import yfinance as yf
from typing import Dict, Any, Callable
from datetime import datetime
import json

def get_stock_price(symbol: str) -> dict:
    """
    Get stock price and additional information with error handling
    """
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
            'market_cap': ticker.info.get('marketCap', 'N/A')
        }
        return info

    except Exception as e:
        return {
            'error': True,
            'message': f"Error fetching data for {symbol}: {str(e)}",
            'symbol': symbol.upper()
        }

get_stock_price_tool = {
    'type': 'function',
    'function': {
        'name': 'get_stock_price',
        'description': 'Get the current stock price and information for any symbol',
        'parameters': {
            'type': 'object',
            'required': ['symbol'],
            'properties': {
                'symbol': {'type': 'string', 'description': 'The stock symbol (e.g., AAPL, GOOGL, MSFT, AMZN)'},
            },
        },
    },
}

def format_stock_output(stock_data: dict) -> str:
    """Format stock information for display"""
    if 'error' in stock_data:
        return f"❌ {stock_data['message']}"

    # Format market cap in billions
    market_cap = stock_data['market_cap']
    if isinstance(market_cap, (int, float)):
        market_cap = f"${market_cap/1e9:.2f}B"

    return f"""
📈 Stock Information for {stock_data['company_name']} ({stock_data['symbol']})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Current Price: {stock_data['currency']} {stock_data['price']:.2f}
• Change: {stock_data['change_percent']:.2f}%
• Volume: {stock_data['volume']:,}
• Market Cap: {market_cap}
• Last Updated: {stock_data['timestamp']}
"""

def process_stock_query(prompt: str):
    """Process a stock-related query"""
    print(f"🔍 Query: {prompt}\n")

    available_functions: Dict[str, Callable] = {
        'get_stock_price': get_stock_price,
    }

    response = ollama.chat(
        'llama3.1',
        messages=[{'role': 'user', 'content': prompt}],
        tools=[get_stock_price_tool],
    )

    # Process only the first tool call
    if response.message.tool_calls:
        tool = response.message.tool_calls[0]  # Take only the first tool call
        if function_to_call := available_functions.get(tool.function.name):
            arguments = tool.function.arguments
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            result = function_to_call(**arguments)
            print(format_stock_output(result))
        else:
            print(f"❌ Function {tool.function.name} not found")

# Test with multiple symbols
symbols = [
    "What is Apple's current stock price?",
    "Show me the stock price for Microsoft (MSFT)",
    "What's Google's (GOOGL) stock price?",
    "Get me Amazon's (AMZN) stock price"
]

# Run one query or test multiple
single_mode = True  # Set to False to test multiple symbols

if single_mode:
    query = "What is Apple's current stock price?"
    process_stock_query(query)
else:
    for query in symbols:
        process_stock_query(query)
        print("\n" + "="*50 + "\n")