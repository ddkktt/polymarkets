import json
import random
import asyncio
import aiohttp
from datetime import datetime
import os
from dotenv import load_dotenv
from typing import List, Dict
import time

# Load environment variables
load_dotenv()

class MarketOpinionAnalyzer:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
        }
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        self.models = [
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3.5-sonnet:beta",
            "google/gemini-flash-1.5",
            "openai/gpt-4-turbo",
            "meta-llama/llama-3.3-70b-instruct",
            "nousresearch/hermes-3-llama-3.1-405b"
        ]

    def create_prompt(self, market: Dict) -> str:
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""Current date: {current_date}

Analyze this prediction market focusing first on its relevance to financial markets:

Market Description: {market['description']}
End Date: {market['end_date']}
Current Prices: Yes: {market['tokens'][0]['price']}, No: {market['tokens'][1]['price']}

Answer these questions in order:
1. Is this market relevant to traditional financial markets or crypto? (Yes/No)
2. Rate the relevance on a scale of 1-100 with brief justification
3. What specific aspects of traditional finance or crypto could be impacted?
4. Based on the current market prices, what is your assessment of market sentiment?

Keep each answer brief (1-2 sentences per point)."""
        return prompt

    async def get_model_opinion(self, session: aiohttp.ClientSession, 
                              market: Dict, model: str) -> Dict:
        try:
            prompt = self.create_prompt(market)
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a financial markets analyst. Provide brief, focused analyses."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            async with session.post(self.api_url, headers=self.headers, json=payload) as response:
                if response.status != 200:
                    return {
                        "model": model,
                        "opinion": f"Error: {response.status}",
                        "error": True
                    }
                
                llm_response = await response.json()
                content = llm_response['choices'][0]['message']['content'].strip()
                
                return {
                    "model": model,
                    "opinion": content,
                    "error": False
                }
                
        except Exception as e:
            return {
                "model": model,
                "opinion": f"Error: {str(e)}",
                "error": True
            }

    async def analyze_market_with_models(self, session: aiohttp.ClientSession, 
                                       market: Dict) -> Dict:
        tasks = []
        for model in self.models:
            # Add delay between model calls to avoid rate limits
            if tasks:  # If not the first task
                await asyncio.sleep(0.5)
            tasks.append(self.get_model_opinion(session, market, model))
        
        opinions = await asyncio.gather(*tasks)
        
        return {
            "market": market,
            "model_opinions": opinions
        }

    def format_market_analysis(self, analysis: Dict) -> str:
        market = analysis['market']
        output = [
            "\n" + "=" * 100,
            f"Market Description: {market['description']}",
            f"End Date: {market['end_date']}",
            f"Current Prices: Yes: {market['tokens'][0]['price']}, No: {market['tokens'][1]['price']}",
            f"Previous Analysis Category: {market['financial_analysis']['category']}",
            f"Previous Relevancy Score: {market['financial_analysis']['relevancy_score']}",
            "\nModel Opinions:",
            "-" * 50
        ]
        
        for opinion in analysis['model_opinions']:
            output.extend([
                f"\nModel: {opinion['model']}",
                "Opinion:" if not opinion['error'] else "Error:",
                opinion['opinion'],
                "-" * 50
            ])
        
        return "\n".join(output)

    async def analyze_markets(self, markets: List[Dict], batch_size: int = 5) -> List[Dict]:
        async with aiohttp.ClientSession() as session:
            all_analyses = []
            
            # Process markets in batches
            for i in range(0, len(markets), batch_size):
                batch = markets[i:i + batch_size]
                print(f"\nProcessing batch {i//batch_size + 1}/{len(markets)//batch_size + 1}")
                
                # Process batch in parallel
                batch_tasks = [self.analyze_market_with_models(session, market) for market in batch]
                batch_results = await asyncio.gather(*batch_tasks)
                all_analyses.extend(batch_results)
                
                print(f"Completed {len(all_analyses)}/{len(markets)} markets")
                
                # Add delay between batches to avoid rate limits
                if i + batch_size < len(markets):
                    print("Waiting between batches...")
            
            return all_analyses

    def save_analysis(self, analyses: List[Dict], output_file: str):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"{output_file}_{timestamp}.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Analysis Time: {datetime.now().isoformat()}\n")
            f.write(f"Number of Markets Analyzed: {len(analyses)}\n\n")
            
            for analysis in analyses:
                f.write(self.format_market_analysis(analysis))
                f.write("\n\n")
        
        # Also save as JSON for potential further processing
        json_file = f"{output_file[:-4]}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_markets": len(analyses),
                "analyses": analyses
            }, f, indent=2)
        
        return output_file, json_file

def main():
    # Load API key
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required")

    # Load analyzed markets
    with open("analyzed_markets20250203_203327.json", 'r') as f:
        data = json.load(f)

    # Sample 50 random markets
    sample_markets = random.sample(data['markets'], 50)
    
    analyzer = MarketOpinionAnalyzer(api_key)
    
    print(f"Starting analysis of {len(sample_markets)} markets...")
    print(f"Using models: {', '.join(analyzer.models)}")
    
    # Run analysis with batch size
    batch_size = 5  # Adjust this value based on API rate limits
    market_analyses = asyncio.run(analyzer.analyze_markets(sample_markets, batch_size))
    # Save results
    txt_file, json_file = analyzer.save_analysis(market_analyses, "market_opinions")
    
    print(f"\nAnalysis complete!")
    print(f"Results saved to:")
    print(f"- Text format: {txt_file}")
    print(f"- JSON format: {json_file}")

if __name__ == "__main__":
    main()