import json
from datetime import datetime

def format_money(value):
    """Format monetary values with commas and 2 decimal places"""
    return f"${value:,.2f}"

def format_probabilities(probs):
    """Format probability dictionary into readable string"""
    return ", ".join(f"{key}: {value:.1f}%" for key, value in probs.items())

def format_category_name(name):
    """Convert category key to readable title"""
    return name.replace('_', ' ').title()

def generate_market_summary(market_data):
    """Generate a summary for a single market"""
    lines = []
    lines.append(f"Market: {market_data['ticker']}")
    lines.append(f"Relevance Score: {market_data['relevance']}")
    lines.append(f"Volume: {format_money(market_data['volume'])}")
    lines.append(f"24hr Volume: {format_money(market_data['volume_24hr'])}")
    lines.append("\nReasoning:")
    lines.append(market_data['reasoning'])
    lines.append("\nIndividual Markets:")
    
    for market in market_data['markets']:
        lines.append(f"\n  {market['question']}")
        lines.append(f"  Probabilities: {format_probabilities(market['probabilities'])}")
    
    return "\n".join(lines)

def generate_category_summary(category_name, markets):
    """Generate a summary for an entire category"""
    lines = []
    lines.append("=" * 80)
    lines.append(f"\n{format_category_name(category_name)}\n")
    lines.append("=" * 80 + "\n")
    
    if not markets:
        lines.append("No markets found in this category.\n")
        return "\n".join(lines)
    
    # Sort markets by volume
    sorted_markets = sorted(markets, key=lambda x: x['volume'], reverse=True)
    
    # Add each market's summary
    for i, market in enumerate(sorted_markets, 1):
        lines.append(f"#{i}")
        lines.append(generate_market_summary(market))
        lines.append("\n" + "-" * 40 + "\n")
    
    return "\n".join(lines)

def generate_summary(categories_data):
    """Generate the complete summary document"""
    lines = []
    
    # Add header
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append("Market Categories Summary")
    lines.append(f"Generated: {current_time}\n")
    
    # Add category statistics
    lines.append("Category Statistics:")
    for category, markets in categories_data.items():
        total_volume = sum(m['volume'] for m in markets)
        lines.append(f"{format_category_name(category)}: {len(markets)} markets, "
                    f"Total Volume: {format_money(total_volume)}")
    lines.append("\n" + "=" * 80 + "\n")
    
    # Add each category's detailed summary
    for category, markets in categories_data.items():
        lines.append(generate_category_summary(category, markets))
    
    return "\n".join(lines)

def main():
    input_file = "categorized_markets.json"
    output_file = "market_categories_summary.txt"
    
    try:
        # Read the categorized markets JSON
        with open(input_file, 'r') as f:
            categories_data = json.load(f)
        
        # Generate the summary
        summary = generate_summary(categories_data)
        
        # Write to output file
        with open(output_file, 'w') as f:
            f.write(summary)
        
        print(f"Successfully wrote summary to {output_file}")
        
    except Exception as e:
        print(f"Error generating summary: {e}")

if __name__ == "__main__":
    main()