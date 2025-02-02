import requests
import pandas as pd
from datetime import datetime
import pytz
from decimal import Decimal
import json

# Constants
CLOB_URL = "https://clob.polymarket.com/prices-history"

HEADERS = {
    'Accept': 'application/json',
    'Origin': 'https://polymarket.com',
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://polymarket.com/'
}

def get_historical_data(asset_id, startTs, fidelity):
    """
    Fetch historical price data for a specific market
    """
    params = {
        'startTs': startTs,
        'market': asset_id,
        'earliestTimestamp': '1704096000',
        'fidelity': fidelity
    }
    
    try:
        response = requests.get(CLOB_URL, params=params, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        print(f"CLOB Response status: {response.status_code}")
        print(f"Data points received: {len(data.get('history', []))}")
        return data.get("history", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching historical data: {e}")
        return []

def generate_df(data, name):
    """Generate a formatted DataFrame from historical data"""
    if not data:
        print("No data received to generate DataFrame")
        return pd.DataFrame(columns=['timestamp', name])
        
    df = pd.DataFrame(data)
    
    if df.empty:
        print("Empty DataFrame created from data")
        return pd.DataFrame(columns=['timestamp', name])
    
    print(f"DataFrame created with {len(df)} rows")
    
    pt_timezone = pytz.timezone('US/Pacific')
    et_timezone = pytz.timezone('US/Eastern')
    
    df['timestamp'] = df['t'].apply(
        lambda x: datetime.fromtimestamp(x, pt_timezone).astimezone(et_timezone).strftime('%B %d, %Y, %-I:%M %p ET')
    )
    df[name] = df['p'].apply(lambda x: f"{x:.4f}")
    
    return df[['timestamp', name]]

if __name__ == "__main__":
    print("Starting data fetch...")
    
    # Use the provided token ID
    TOKEN_ID = "106865576428777407916141564093257614374265521997189562130356916415413780799391"
    
    print(f"\nFetching historical data for token {TOKEN_ID}...")
    data = get_historical_data(
        asset_id=TOKEN_ID,
        startTs="1704096000",  # January 1, 2024
        fidelity="1440"
    )
    
    if data:
        print("\nGenerating DataFrame...")
        df = generate_df(data, "price")
        print("\nHistorical Data:")
        print(df)
        print(f"\nTotal rows: {len(df)}")
    else:
        print("No historical data found for this token")