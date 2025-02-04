import json
from datetime import datetime
import re

def clean_json_string(json_str):
    if not json_str:
        return ""
    last_complete = json_str.rfind('}]}')
    if last_complete != -1:
        return json_str[:last_complete + 3] + '}]}'
    return json_str

def format_price(price):
    try:
        return f"{float(price) * 100:.1f}%"
    except (ValueError, TypeError):
        return "N/A"

def format_date(date_str):
    if not date_str:
        return "N/A"
    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%B %d, %Y")
        except ValueError:
            continue
    return "N/A"

def parse_markets(file_path):
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return ""
    
    clean_content = clean_json_string(content)
    if not clean_content:
        print("Cleaned content is empty")
        return ""
    
    try:
        data = json.loads(clean_content)
        print(f"Successfully loaded JSON. Data keys: {data.keys()}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return ""
    
    formatted_output = []
    formatted_output.append("Individual Markets:\n")
    
    if 'results' not in data:
        print("No results found in data")
        return "\n".join(formatted_output)
    
    for result in data.get('results', []):
        print(f"Processing result: {result}")
        market = result.get('market_details', {})
        formatted_output.append("\n" + "="*50 + "\n")
        formatted_output.append(f"Question: {market.get('ticker', 'N/A')}")
        formatted_output.append(f"Start Date: {format_date(market.get('startDate', ''))}")
        formatted_output.append(f"End Date: {format_date(market.get('endDate', ''))}")
        formatted_output.append(f"Total Volume: ${float(market.get('volume', 0)):,.2f}")
        
        volume24hr = market.get('volume24hr', None)
        if volume24hr is not None:
            formatted_output.append(f"24hr Volume: ${float(volume24hr):,.2f}")
        else:
            formatted_output.append("24hr Volume: N/A")
        
        for detail in market.get('markets_detail', []):
            print(f"Processing market detail: {detail}")
            formatted_output.append("\n" + "-"*40 + "\n")
            
            
            outcomes = json.loads(detail.get('outcomes', '[]') or '[]')
            prices = json.loads(detail.get('outcomePrices', '[]') or '[]')
            
            print(f"Outcomes parsed: {outcomes}")
            print(f"Prices parsed: {prices}")
            prob = None
            probabilities = []
            for outcome, price in zip(outcomes, prices):
                if price:
                    probabilities.append(f"{outcome}: {float(price)*100:.1f}%")
                else:
                    probabilities.append(f"{outcome}: N/A")
            
            print(f"Probabilities: {probabilities}")
            
            if len(probabilities) >= 2:
                formatted_output.append("Current Probabilities: Yes: {}, No: {}".format(
                    probabilities[0].split(': ')[1], probabilities[1].split(': ')[1]))
            elif len(probabilities) == 1:
                prob = probabilities[0]
            else:
                prob = "Current Probabilities: N/A"
            formatted_output.append(f"{detail.get('question', 'N/A')} {prob}")
            volume24hr_detail = detail.get('volume24hr', None)

    return "\n".join(formatted_output)

def main():
    input_file = "markets-preAnalyzed/market_analysis_processed.json"
    output_file = "formatted_markets2.txt"
    
    try:
        print(f"Processing file: {input_file}")
        formatted_data = parse_markets(input_file)
        if formatted_data:
            print(f"Writing output to: {output_file}")
            with open(output_file, 'w') as f:
                f.write(formatted_data)
            print(f"Successfully wrote {len(formatted_data)} characters to output file")
        else:
            print("No data to write")
    except Exception as e:
        print(f"Critical error occurred: {str(e)}")

if __name__ == "__main__":
    main()