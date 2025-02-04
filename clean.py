import json
from datetime import datetime
import re

def print_debug(label, data):
    """Helper function to print debug information"""
    print(f"\n=== {label} ===")
    print(type(data))
    try:
        if isinstance(data, str) and len(data) > 500:
            print(data[:500] + "...")
        else:
            print(data)
    except Exception as e:
        print(f"Error printing data: {e}")

def safe_float(value, default=0.0):
    """Safely convert value to float, handling None values"""
    try:
        if value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_json_loads(value, default=None):
    """Safely load JSON string, handling None values"""
    try:
        if value is None:
            return default
        return json.loads(value)
    except json.JSONDecodeError:
        return default

def extract_json_from_markdown(content):
    """Extract JSON from markdown code blocks"""
    try:
        if not content:
            return None
        # Find content between ```json and ```
        json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        return None
    except Exception as e:
        print_debug("Error extracting JSON from markdown", str(e))
        return None

def parse_analysis(analysis):
    """Parse the analysis field to extract the actual analysis content"""
    try:
        if not isinstance(analysis, dict):
            return None
        
        choices = analysis.get('choices', [])
        if not choices:
            return None
            
        message = choices[0].get('message', {})
        if not message:
            return None
            
        content = message.get('content')
        if not content:
            return None
            
        return extract_json_from_markdown(content)
    except Exception as e:
        print_debug("Error parsing analysis", str(e))
        return None

def parse_markets(input_file):
    """Parse market data from the pre-analyzed JSON file"""
    print_debug("Reading file", input_file)
    
    try:
        with open(input_file, 'r') as f:
            content = f.read()
        print_debug("Raw content first 500 chars", content)
        
        # Try to parse the content as JSON first
        try:
            raw_data = json.loads(content)
            print_debug("Successfully parsed JSON", "Structure: " + str(list(raw_data.keys()) if isinstance(raw_data, dict) else "Not a dict"))
        except json.JSONDecodeError as e:
            print_debug("JSON Parse Error", str(e))
            # Clean the JSON string if needed
            last_complete = content.rfind('}]}')
            if last_complete != -1:
                content = content[:last_complete + 3] + '}]}'
                print_debug("Cleaned JSON", f"Length: {len(content)}")
                raw_data = json.loads(content)
        
        print_debug("Raw data keys", list(raw_data.keys()) if isinstance(raw_data, dict) else "Not a dict")
        
        # Start building structured data
        structured_data = {
            "timestamp": raw_data.get("timestamp", ""),
            "total_markets": raw_data.get("total_markets", 0),
            "markets": []
        }
        
        print_debug("Basic info extracted", structured_data)
        
        # Try to process each market
        for result in raw_data.get('results', []):
            print_debug("Processing result", result.keys() if isinstance(result, dict) else "Not a dict")
            try:
                market = result.get('market_details', {})
                
                market_data = {
                    "metadata": {
                        "ticker": market.get('ticker', ''),
                        "start_date": market.get('startDate', ''),
                        "end_date": market.get('endDate', ''),
                        "volume": safe_float(market.get('volume')),
                        "volume_24hr": safe_float(market.get('volume24hr'))
                    },
                    "markets": []
                }
                
                # Process individual markets
                for detail in market.get('markets_detail', []):
                    try:
                        outcomes = safe_json_loads(detail.get('outcomes'), [])
                        prices = safe_json_loads(detail.get('outcomePrices'), [])
                        
                        if outcomes and prices:
                            market_detail = {
                                "question": detail.get('question', ''),
                                "probabilities": {
                                    outcome: safe_float(price) * 100
                                    for outcome, price in zip(outcomes, prices)
                                }
                            }
                            
                            volume_24hr = detail.get('volume24hr')
                            if volume_24hr is not None:
                                market_detail["volume_24hr"] = safe_float(volume_24hr)
                            
                            market_data["markets"].append(market_detail)
                    except Exception as e:
                        print_debug("Error processing detail", f"{str(e)}\nDetail: {detail}")
                        continue
                
                # Add analysis if present
                if 'analysis' in result:
                    analysis_content = parse_analysis(result['analysis'])
                    if analysis_content:
                        market_data['analysis'] = analysis_content
                
                structured_data["markets"].append(market_data)
            except Exception as e:
                print_debug("Error processing market", str(e))
                continue
        
        print_debug("Final structured data", f"Length: {len(str(structured_data))}")
        return structured_data
        
    except Exception as e:
        print_debug("Top level error", str(e))
        raise

def categorize_markets(markets_data):
    """Create categorized view of markets based on analysis relevance"""
    categories = {
        "economic_indicators": [],
        "geopolitical_events": [],
        "regulatory_changes": [],
        "technological_developments": []
    }
    
    # Mapping from analysis keys to category names
    category_mapping = {
        "economic_indicators": "economic_indicators",
        "geopolitical_events": "geopolitical_events",
        "regulatory_changes": "regulatory_changes",
        "technological_developments": "technological_developments"
    }
    
    for market in markets_data["markets"]:
        analysis = market.get("analysis", {})
        
        # Skip if no analysis
        if not analysis:
            continue
            
        # Check each category
        for analysis_key, category_name in category_mapping.items():
            category_data = analysis.get(analysis_key, {})
            relevance = safe_float(category_data.get("relevance", 0))
            
            # Add to category if relevance >= 9
            if relevance >= 9:
                market_summary = {
                    "ticker": market["metadata"]["ticker"],
                    "relevance": relevance,
                    "reasoning": category_data.get("reasoning", ""),
                    "volume": market["metadata"]["volume"],
                    "volume_24hr": market["metadata"]["volume_24hr"],
                    "markets": [
                        {
                            "question": m["question"],
                            "probabilities": m["probabilities"]
                        }
                        for m in market["markets"]
                    ]
                }
                categories[category_name].append(market_summary)
    
    return categories


def main():
    input_file = "markets-preAnalyzed/market_analysis_final_20250204_012032.json"
    
    try:
        # Parse market data
        market_data = parse_markets(input_file)
        
        # Save full market data
        with open("formatted_markets.json", 'w') as f:
            json.dump(market_data, f, indent=2)
        
        # Create and save categorized view
        categorized_data = categorize_markets(market_data)
        with open("categorized_markets.json", 'w') as f:
            json.dump(categorized_data, f, indent=2)
            
        print("\nSuccessfully wrote formatted data to formatted_markets.json")
        print("Successfully wrote categorized data to categorized_markets.json")
        
    except Exception as e:
        print(f"\nError processing file: {e}")

if __name__ == "__main__":
    main()