import json
import logging
import os
import aiohttp
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
)

class OpenRouterClient:
    def __init__(self):
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers={
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    async def analyze_market(self, market_content: str) -> Dict:
        """Send market analysis request to OpenRouter API"""
        try:
            payload = {
                "model": "deepseek/deepseek-r1",
                "messages": [
                    {
                        "role": "user",
                        "content": market_content
                    }
                ]
            }
            
            async with self.session.post(self.base_url, json=payload) as response:
                response.raise_for_status()
                return await response.json()
                
        except Exception as e:
            logging.error(f"API request failed: {str(e)}")
            raise
            
    async def analyze_markets_batch(self, contents: List[str]) -> List[Dict]:
        """Process multiple markets concurrently"""
        tasks = [self.analyze_market(content) for content in contents]
        return await asyncio.gather(*tasks, return_exceptions=True)

class ConsolidatedMarketValidator:
    def __init__(self, input_file: str, batch_size: int = 50):
        """Initialize the validator with input file and batch size"""
        try:
            with open(input_file, 'r') as f:
                self.data = json.load(f)
            self.batch_size = batch_size
            logging.info(f"Successfully loaded input file: {input_file}")
        except Exception as e:
            logging.error(f"Error loading input file: {str(e)}", exc_info=True)
            raise

    def extract_market_details(self, market: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant market details"""
        return {
            "ticker": market.get('ticker'),
            "slug": market.get('slug'),
            "startDate": market.get('startDate'),
            "endDate": market.get('endDate'),
            "liquidity": market.get('liquidity'),
            "volume": market.get('volume'),
            "volume24hr": market.get('volume24hr'),
            "competitive": market.get('competitive'),
            "markets_detail": [
                {
                    "id": detail.get('id'),
                    "question": detail.get('question'),
                    "conditionId": detail.get('conditionId'),
                    "endDate": detail.get('endDate'),
                    "liquidity": detail.get('liquidity'),
                    "outcomes": detail.get('outcomes'),
                    "outcomePrices": detail.get('outcomePrices'),
                    "volume": detail.get('volume'),
                    "volume24hr": detail.get('volume24hr'),
                    "clobTokenIds": detail.get('clobTokenIds'),
                    "competitive": detail.get('competitive'),
                    "description": detail.get('description')
                }
                for detail in market.get('markets_detail', [])
            ]
        }

    def parse_outcome_prices(self, detail: Dict[str, Any]) -> float:
        """Safely parse outcome prices and return probability"""
        try:
            prices = detail.get('outcomePrices')
            if prices is None:
                return 0.0
            if isinstance(prices, str):
                prices = json.loads(prices)
            if isinstance(prices, list) and len(prices) > 0:
                return float(prices[0])
            return 0.0
        except (ValueError, json.JSONDecodeError):
            return 0.0

    def is_price_market(self, question: str) -> bool:
        """Check if the market is price-based"""
        return '$' in question and any(word in question.lower() for word in ['reach', 'dip'])

    def extract_price(self, question: str) -> float:
        """Extract price from question safely"""
        try:
            price_str = question.split('$')[1].split()[0].replace(',', '')
            return float(price_str)
        except (IndexError, ValueError):
            return 0.0

    def format_market_overview(self, market_data: Dict[str, Any], details: List[Dict[str, Any]]) -> str:
        """Format market overview section"""
        try:
            end_date = details[0].get('endDate', 'Unknown') if details else 'Unknown'
            return f"""Market Overview:
- Total Volume: ${float(market_data.get('volume', 0)):,.2f}
- Total Liquidity: ${float(market_data.get('liquidity', 0)):,.2f}
- 24hr Volume: ${float(market_data.get('volume24hr', 0)):,.2f}
- Market End Date: {end_date}"""
        except (ValueError, TypeError):
            return "Market Overview: Data unavailable"

    def create_price_market_prompt(self, market_data: Dict[str, Any], details: List[Dict[str, Any]]) -> str:
        """Create prompt for price-based markets"""
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Sort questions by price target
        details.sort(key=lambda x: self.extract_price(x['question']))
        
        # Create price options string
        price_options = []
        for detail in details:
            if not self.is_price_market(detail['question']):
                continue
            price = detail['question'].split('$')[1].split()[0]
            direction = "reach" if "reach" in detail['question'].lower() else "dip to"
            yes_prob = self.parse_outcome_prices(detail)
            price_options.append(f"${price}: {direction} ({yes_prob:.1%} probability)")

        market_overview = self.format_market_overview(market_data, details)
        
        return f"""Market Analysis ({current_date})

{market_overview}

Price Targets:
{chr(10).join(f"- {option}" for option in price_options)}"""

    def create_regular_market_prompt(self, market_data: Dict[str, Any], details: List[Dict[str, Any]]) -> str:
        """Create prompt for non-price markets"""
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Create options string
        options = []
        for detail in details:
            yes_prob = self.parse_outcome_prices(detail)
            options.append(f"{detail['question']} ({yes_prob:.1%} probability)")

        market_overview = self.format_market_overview(market_data, details)
        
        return f"""Market Analysis ({current_date})

{market_overview}

Questions:
{chr(10).join(f"- {option}" for option in options)}"""

    def create_consolidated_prompt(self, market_data: Dict[str, Any], details: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create consolidated prompt based on market type"""
        if not details:
            return {
                "ticker": market_data.get('ticker', 'unknown'),
                "prompt": "No market details available"
            }

        # Check if this is a price market based on first question
        is_price = self.is_price_market(details[0]['question']) if details else False
        
        market_info = (self.create_price_market_prompt(market_data, details) 
                      if is_price 
                      else self.create_regular_market_prompt(market_data, details))

        assessment_template = """
Assess the market's relevance to these key areas:
1. Economic indicators (CPI, interest rates, recessions)
2. Geopolitical events (elections, wars, sanctions)
3. Regulatory changes (crypto, financial markets)
4. Technological developments (AI, tech innovations)

For each area, provide:
- A yes/no assessment of potential impact
- A relevance score from 1-10 
- Brief reasoning for your assessment

Respond STRICTLY in this JSON format:
{
    "economic_indicators": {
        "impact": true/false,
        "relevance": 1-10,
        "reasoning": "..."
    },
    "geopolitical_events": {
        "impact": true/false,
        "relevance": 1-10,
        "reasoning": "..."
    },
    "regulatory_changes": {
        "impact": true/false,
        "relevance": 1-10,
        "reasoning": "..."
    },
    "technological_developments": {
        "impact": true/false,
        "relevance": 1-10,
        "reasoning": "..."
    }
    "market_metadata": {
    "time_horizon": "short/medium/long",
    "confidence_score": 1-10,
    "potential_correlations": ["related_market_ids"],
    "update_frequency": "how often this should be reassessed"
    }
}"""

        prompt = f"Market: {market_data.get('ticker', 'unknown')}\n{market_info}\n{assessment_template}"
        
        return {
            "ticker": market_data.get('ticker', 'unknown'),
            "prompt": prompt
        }
    
    async def process_batch(self, batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a batch of markets concurrently"""
        batch_results = []
        market_contents = []
        market_details = []
        
        # Prepare all market contents and details
        for market in batch:
            try:
                details = self.extract_market_details(market)
                formatted_payload = self.create_consolidated_prompt(
                    market,
                    market.get('markets_detail', [])
                )
                
                market_contents.append(formatted_payload['prompt'])
                market_details.append(details)
                logging.info(f"Prepared market: {formatted_payload['ticker']}")
                
            except Exception as e:
                logging.error(f"Error preparing market {market.get('ticker', 'unknown')}: {str(e)}")
                continue
        
        # Process all markets concurrently
        async with OpenRouterClient() as client:
            analysis_results = await client.analyze_markets_batch(market_contents)
            
            # Combine results with market details
            for i, (details, analysis) in enumerate(zip(market_details, analysis_results)):
                if isinstance(analysis, Exception):
                    logging.error(f"Error analyzing market {details['ticker']}: {str(analysis)}")
                    continue
                    
                batch_results.append({
                    "market_details": details,
                    "analysis": analysis
                })
                logging.info(f"Successfully analyzed market: {details['ticker']}")
        
        return batch_results

    async def validate_and_analyze_markets(self):
        """Validate markets and send them to OpenRouter for analysis in batches"""
        logging.info("Starting validation and analysis of consolidated markets")
        
        all_markets = self.data.get('markets', [])
        total_markets = len(all_markets)
        results = []
        
        for i in range(0, total_markets, self.batch_size):
            batch = all_markets[i:i + self.batch_size]
            batch_number = (i // self.batch_size) + 1
            total_batches = (total_markets + self.batch_size - 1) // self.batch_size
            
            logging.info(f"Processing batch {batch_number} of {total_batches}")
            
            batch_results = await self.process_batch(batch)
            results.extend(batch_results)
            
            self.save_results(results, batch_number)
            
            logging.info(f"Completed batch {batch_number} of {total_batches}")
            
        return results

    def save_results(self, results: List[Dict[str, Any]], batch_number: int):
        """Save results to a JSON file"""
        output_file = f"market_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}_batch_{batch_number}.json"
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_markets": len(results),
                "results": results
            }, f, indent=2)
        logging.info(f"Results saved to {output_file}")

async def main():
    input_file = 'refined_markets_20250203_223503.json'
    batch_size = 100  # Process 100 markets at a time

    try:
        validator = ConsolidatedMarketValidator(input_file, batch_size)
        results = await validator.validate_and_analyze_markets()
        
        # Save final results
        output_file = f"market_analysis_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total_markets": len(results),
                "results": results
            }, f, indent=2)
        logging.info(f"Final analysis results saved to {output_file}")
        
    except Exception as e:
        logging.error(f"Unexpected error in main: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())