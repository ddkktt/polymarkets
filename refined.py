import json
from datetime import datetime

def process_markets_file(filename):
    """
    Process the markets JSON file and extract specific fields
    """
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        
        refined_markets = []
        
        for market in data['markets']:
            refined_market = {
                'ticker': market.get('ticker'),
                'slug': market.get('slug'),
                'date': market.get('date'),
                'startDate': market.get('startDate'),
                'creationDate': market.get('creationDate'),
                'endDate': market.get('endDate'),
                'liquidity': market.get('liquidity'),
                'volume': market.get('volume'),
                'openInterest': market.get('openInterest'),
                'competitive': market.get('competitive'),
                'volume24hr': market.get('volume24hr'),
                'liquidityClob': market.get('liquidityClob'),
                'markets_detail': []
            }
            
            # Process nested markets
            for sub_market in market.get('markets', []):
                refined_sub_market = {
                    'id': sub_market.get('id'),
                    'question': sub_market.get('question'),
                    'conditionId': sub_market.get('conditionId'),
                    'slug': sub_market.get('slug'),
                    'endDate': sub_market.get('endDate'),
                    'liquidity': sub_market.get('liquidity'),
                    'description': sub_market.get('description'),
                    'outcomes': sub_market.get('outcomes'),
                    'outcomePrices': sub_market.get('outcomePrices'),
                    'volume': sub_market.get('volume'),
                    'volumeNum': sub_market.get('volumeNum'),
                    'liquidityNum': sub_market.get('liquidityNum'),
                    'volume24hr': sub_market.get('volume24hr'),
                    'clobTokenIds': sub_market.get('clobTokenIds'),
                    'volume24hrClob': sub_market.get('volume24hrClob'),
                    'volumeClob': sub_market.get('volumeClob'),
                    'liquidityClob': sub_market.get('liquidityClob'),
                    'competitive': sub_market.get('competitive'),
                    'bestBid': sub_market.get('bestBid'),
                    'bestAsk': sub_market.get('bestAsk'),
                    'lastTradePrice': sub_market.get('lastTradePrice'),
                    'oneDayPriceChange': sub_market.get('oneDayPriceChange'),
                    'spread': sub_market.get('spread')
                }
                refined_market['markets_detail'].append(refined_sub_market)
            
            refined_markets.append(refined_market)
        
        # Save refined data
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"refined_markets_{timestamp}.json"
        
        with open(output_filename, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_markets': len(refined_markets),
                'markets': refined_markets
            }, f, indent=2)
        
        print(f"Processed {len(refined_markets)} markets")
        print(f"Refined data saved to: {output_filename}")
        
        # Print first market as example
        if refined_markets:
            print("\nExample of refined market data (first market):")
            print(json.dumps(refined_markets[0], indent=2))
            
    except Exception as e:
        print(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    # You can replace this with your actual filename
    input_filename = "filtered_markets_20250203_222828.json"
    process_markets_file(input_filename)