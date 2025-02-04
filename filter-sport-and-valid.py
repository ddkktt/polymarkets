import json
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_markets(filename):
    """Load markets from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

def is_sports_related(text, exclude_terms):
    """Check if text contains any sports-related terms."""
    if not text:
        return False
    
    text = text.lower()
    return any(term.lower() in text for term in exclude_terms)

def has_valid_tokens(market):
    """Check if market has valid token IDs."""
    tokens = market.get('tokens', [])
    if not tokens:
        return False
    
    # Check that we have at least one token and all tokens have non-empty token_ids
    return all(
        'token_id' in token and 
        token['token_id'] and  # Check for non-empty string
        isinstance(token['token_id'], str) and  # Ensure it's a string
        token['token_id'].strip()  # Check it's not just whitespace
        for token in tokens
    )

def filter_markets(markets_data, exclude_terms):
    """Filter out sports-related markets and those without valid token IDs."""
    filtered_markets = []
    removed_sports_markets = []
    removed_invalid_markets = []
    
    for market in markets_data['markets']:
        # First check for valid tokens
        if not has_valid_tokens(market):
            logger.debug(f"Removing market due to invalid tokens: {market.get('question', 'No question')} | {market.get('condition_id', 'No ID')}")
            removed_invalid_markets.append(market)
            continue

        # Then check for sports terms
        description = market.get('description', '')
        question = market.get('question', '')
        category = market.get('category', '')
        
        combined_text = f"{description} {question} {category}"
        
        if is_sports_related(combined_text, exclude_terms):
            removed_sports_markets.append(market)
        else:
            filtered_markets.append(market)
    
    return filtered_markets, removed_sports_markets, removed_invalid_markets

def save_markets(markets, filename):
    """Save markets to a JSON file."""
    output = {
        'timestamp': datetime.now().isoformat(),
        'total_markets': len(markets),
        'markets': markets
    }
    
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

def main():
    try:
        # Define exclusion terms
        exclude_terms = [
            'nba', 'nfl', 'mlb', 'nhl', 'fifa', 'stanley cup', 
            'world cup', 'super bowl', 'football', 'basketball',
            'baseball', 'hockey', 'soccer', 'tennis', 'olympics',
            'post', 'sport', 'ufc', 'boxing', 'mma', 'wrestling', 'wwe',
            'formula 1', 'f1', 'racing', 'grand prix',            'french open', 'roland garros', 'wimbledon', 
            'us open', 'australian open', 'grand slam',
            'ncaa'
        ]
        
        # Load markets
        input_file = "markets_20250203_214226.json"
        markets_data = load_markets(input_file)
        logger.info(f"Loaded {len(markets_data['markets'])} markets")
        
        # Filter markets
        filtered_markets, removed_sports, removed_invalid = filter_markets(markets_data, exclude_terms)
        
        # Save filtered markets
        output_file = f"filtered_markets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_markets(filtered_markets, output_file)
        logger.info(f"Filtered markets saved to {output_file}")
        
        # Save removed sports markets
        sports_file = f"sports_markets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_markets(removed_sports, sports_file)
        
        # Save invalid markets
        invalid_file = f"invalid_markets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_markets(removed_invalid, invalid_file)
        
        # Print statistics
        total_original = len(markets_data['markets'])
        total_filtered = len(filtered_markets)
        total_sports = len(removed_sports)
        total_invalid = len(removed_invalid)
        
        logger.info("\nFiltering Statistics:")
        logger.info(f"Original markets: {total_original}")
        logger.info(f"Remaining markets: {total_filtered}")
        logger.info(f"Removed sports markets: {total_sports}")
        logger.info(f"Removed invalid markets: {total_invalid}")
        logger.info(f"Total removed: {total_sports + total_invalid} ({((total_sports + total_invalid) / total_original) * 100:.1f}%)")
        
        # Sample check of first few markets to verify token IDs
        logger.info("\nVerifying first 5 filtered markets have valid token IDs:")
        for i, market in enumerate(filtered_markets[:5]):
            tokens = market.get('tokens', [])
            logger.info(f"Market {i+1} token IDs: {[t.get('token_id') for t in tokens]}")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()