rom py_clob_client.client import ClobClient
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get environment variables
host: str = os.getenv('CLOB_HOST', 'https://clob.polymarket.com/')
key: str = os.getenv('API_KEY')
chain_id: int = int(os.getenv('CHAIN_ID', '137'))

# Verify required environment variables are present
if not key:
    raise ValueError("API_KEY must be set in environment variables")

# Initialization of a client that trades directly from an EOA
client = ClobClient(host, key=key, chain_id=chain_id)

def get_and_save_filtered_markets(client):
    """
    Fetches active markets containing specific keywords and saves to JSON.
    Keywords: tariff/tarrif, fed, china, russia, ukraine
    """
    next_cursor = ""
    keywords = ['tariff', 'tarrif', 'fed', 'china', 'russia', 'ukraine']
    filtered_markets = []
    
    while True:
        try:
            response = client.get_markets(next_cursor=next_cursor)
            
            for market in response.get('data', []):
                # Check if market is active and contains keywords
                description = market.get('description', '').lower()
                is_active = market.get('active', False)
                
                if is_active and any(keyword in description for keyword in keywords):
                    # Create market entry for JSON
                    market_data = {
                        'condition_id': market.get('condition_id', 'N/A'),
                        'description': market.get('description', 'N/A'),
                        'category': market.get('category', 'N/A'),
                        'token_ids': [token.get('token_id', 'N/A') for token in market.get('tokens', [])]
                    }
                    
                    # Add to filtered markets list
                    filtered_markets.append(market_data)
                    
                    # Print market info
                    print(f"Condition ID: {market_data['condition_id']}")
                    print(f"Description: {market_data['description']}")
                    print(f"Category: {market_data['category']}")
                    print(f"Token IDs: {', '.join(market_data['token_ids'])}")
                    print("-" * 50)
            
            # Check if there are more pages
            next_cursor = response.get('next_cursor', '')
            if not next_cursor or next_cursor == 'LTE=':
                break
                
        except Exception as e:
            print(f"Error fetching markets: {str(e)}")
            break
    
    # Save to JSON file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"filtered_markets_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_markets': len(filtered_markets),
            'markets': filtered_markets
        }, f, indent=2)
    
    print(f"\nFound {len(filtered_markets)} matching markets")
    print(f"Results saved to: {filename}")
    print("Done!")

if __name__ == "__main__":
    resp = get_and_save_filtered_markets(client)
