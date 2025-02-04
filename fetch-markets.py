import httpx
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import asyncio

# Define exclude terms
exclude_terms = [
   
]

async def get_filtered_markets(
    limit: int = 400,
    offset: int = 0,
    active: bool = True,
    archived: bool = False,
    closed: bool = False
):
    """
    Fetches markets from Polymarket API, prints raw JSON, and saves both filtered and unfiltered data
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://gamma-api.polymarket.com/events",
                params={
                    "limit": limit,
                    "active": active,
                    "archived": archived,
                    "closed": closed,
                    "order": "volume24hr",
                    "ascending": False,
                    "offset": offset
                }
            )
            
            if response.status_code != 200:
                print(f"Error fetching markets: {response.text}")
                return
            
            # Get raw response
            markets_data = response.json()
            
            # Print raw JSON with pretty formatting
            print("Raw JSON response:")
            print(json.dumps(markets_data, indent=2))
            
            # Filter markets
            filtered_markets = [
                market for market in markets_data 
                if not any(term.lower() in market.get('title', '').lower() for term in exclude_terms)
            ]
            
            # Print filtered JSON
            print("\nFiltered JSON response (excluding sports terms):")
            print(json.dumps(filtered_markets, indent=2))
            
            # Save both raw and filtered data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_filename = f"raw_markets_{timestamp}.json"
            filtered_filename = f"filtered_markets_{timestamp}.json"
            
            # Save raw data
            with open(raw_filename, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'total_markets': len(markets_data),
                    'markets': markets_data
                }, f, indent=2)
            
            # Save filtered data
            with open(filtered_filename, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'total_markets': len(filtered_markets),
                    'markets': filtered_markets
                }, f, indent=2)
            
            print(f"\nRaw data saved to: {raw_filename}")
            print(f"Filtered data saved to: {filtered_filename}")
            print(f"Total markets received: {len(markets_data)}")
            print(f"Markets after filtering: {len(filtered_markets)}")

    except:
        None

if __name__ == "__main__":
    asyncio.run(get_filtered_markets())