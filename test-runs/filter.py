import json
import requests
from datetime import datetime
import time
from typing import Dict, List, Optional
import os
from concurrent.futures import ThreadPoolExecutor
import asyncio
import aiohttp
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MarketAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
        }
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
    def create_prompt(self, market: Dict) -> str:
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""Current date: {current_date}

Analyze this prediction market for its relevance to traditional financial markets (TradFi) or cryptocurrency markets.

Market Description: {market['description']}
End Date: {market['end_date']}
Current Prices: Yes: {market['tokens'][0]['price']}, No: {market['tokens'][1]['price']}

You must respond with a valid JSON object containing these exact fields:
1. "is_relevant": boolean (true if relevant to financial markets)
2. "category": string (one of: "Macro-economic", "Commodities", "Forex", "Geopolitics", "Crypto", "Technology", "Regulatory", "None")
3. "relevancy_score": number between 1-100
4. "reasoning": string (brief explanation)

Example response:
{{"is_relevant": true, "category": "Macro-economic", "relevancy_score": 85, "reasoning": "Direct impact on interest rates"}}

Response must be a single JSON object and nothing else."""
        return prompt

    async def analyze_market_async(self, session: aiohttp.ClientSession, market: Dict) -> Optional[Dict]:
        try:
            prompt = self.create_prompt(market)
            
            # Truncate description for display
            short_desc = market['description'][:200] + "..." if len(market['description']) > 200 else market['description']
            print(f"\nAnalyzing market:\n{short_desc}\n")
            
            payload = {
                "model": "meta-llama/llama-3.3-70b-instruct",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a financial markets analyst. Always respond with valid JSON objects exactly as requested."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            async with session.post(self.api_url, headers=self.headers, json=payload) as response:
                if response.status != 200:
                    print(f"Error analyzing market {market['condition_id']}: {response.status}")
                    return None
                
                try:
                    llm_response = await response.json()
                    content = llm_response['choices'][0]['message']['content'].strip()
                    content = content.replace('```json', '').replace('```', '').strip()
                    
                    analysis = json.loads(content)
                    
                    if analysis.get('is_relevant'):
                        market_data = {
                            **market,
                            "financial_analysis": {
                                "category": analysis['category'],
                                "relevancy_score": analysis['relevancy_score'],
                                "reasoning": analysis['reasoning']
                            }
                        }
                        print(f"\nRelevant Market Found:")
                        print(f"Category: {analysis['category']}")
                        print(f"Relevancy Score: {analysis['relevancy_score']}")
                        print(f"Reasoning: {analysis['reasoning']}\n")
                        print("-" * 80)
                        return market_data
                    else:
                        print(f"Market deemed irrelevant: {market['condition_id']}")
                    
                    return None
                    
                except json.JSONDecodeError as e:
                    print(f"Error parsing LLM response for market {market['condition_id']}")
                    print(f"Raw response: {content}")
                    return None
                
        except Exception as e:
            print(f"Error processing market {market['condition_id']}: {str(e)}")
            return None

    async def process_markets_async(self, markets: List[Dict], batch_size: int =100) -> List[Dict]:
        """Process markets in parallel batches"""
        relevant_markets = []
        
        async with aiohttp.ClientSession() as session:
            for i in range(0, len(markets), batch_size):
                batch = markets[i:i + batch_size]
                tasks = [self.analyze_market_async(session, market) for market in batch]
                results = await asyncio.gather(*tasks)
                
                for result in results:
                    if result:
                        relevant_markets.append(result)
                
                # Add a small delay between batches to avoid rate limiting
                if i + batch_size < len(markets):
                    await asyncio.sleep(1)
        
        return relevant_markets

    def process_markets(self, input_file: str, output_file: str, batch_size: int = 5):
        """
        Process markets with parallel API calls
        """
        # Load market data
        with open(input_file, 'r') as f:
            market_data = json.load(f)
        
        # Filter active markets
        active_markets = market_data['markets']
        
        print(f"\nFound {len(active_markets)} active markets to analyze")
        print("Starting analysis with parallel processing...")
        print("-" * 80)
        
        # Process markets using asyncio
        relevant_markets = asyncio.run(self.process_markets_async(active_markets, batch_size))
                    
        # Create output data structure
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "total_markets_analyzed": len(active_markets),
            "total_relevant_markets": len(relevant_markets),
            "markets": relevant_markets
        }
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_file + timestamp
        # Save results
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        return output_data

def main():
    # Load API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")
    
    analyzer = MarketAnalyzer(api_key)
    
    # Process markets
    result = analyzer.process_markets(
        input_file="filtered_markets_20250203_185621.json",
        output_file="analyzed_markets.json",
        batch_size=500  # Process 5 markets in parallel
    )
    
    print(f"\nAnalysis complete!")
    print(f"Processed {result['total_markets_analyzed']} markets")
    print(f"Found {result['total_relevant_markets']} relevant markets")
    print(f"Results saved to analyzed_markets.json")

if __name__ == "__main__":
    main()