import json
from typing import Dict, List, Optional
import statistics
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clean_json_content(content: str) -> str:
    """Clean markdown code block markers from JSON content."""
    try:
        if not isinstance(content, str):
            raise ValueError(f"Expected string content, got {type(content)}")
        
        # Remove ```json from start and ``` from end
        if content.startswith('```json\n'):
            content = content[8:]
        if content.endswith('\n```'):
            content = content[:-4]
        return content.strip()
    except Exception as e:
        logger.error(f"Error cleaning JSON content: {str(e)}")
        return ""

def parse_analysis_safely(market: Dict) -> Optional[Dict]:
    """Safely parse the analysis content from a market entry."""
    try:
        if not market.get('analysis'):
            return None
            
        # Get the analysis content
        analysis = market['analysis']
        content = None
        
        # Handle different analysis formats
        if isinstance(analysis, str):
            content = analysis
        elif isinstance(analysis, dict):
            if 'choices' in analysis:
                choices = analysis.get('choices', [])
                if choices and len(choices) > 0:
                    content = choices[0].get('message', {}).get('content')
            else:
                # If it's already a valid JSON object, just return it
                if all(key in analysis for key in ['economic_indicators', 'geopolitical_events', 'regulatory_changes', 'technological_developments']):
                    return analysis
                content = json.dumps(analysis)
                
        if not content:
            logger.warning("No valid content found in analysis")
            return None
            
        # Initial cleanup
        cleaned_content = clean_json_content(content)
        if not cleaned_content:
            return None
            
        # Fix common JSON formatting issues
        cleaned_content = (cleaned_content
            .replace('reascoreoning', 'reasoning')  # Fix known typo
            .replace('\n', '')  # Remove newlines
            .replace('\\n', '')  # Remove escaped newlines
            .replace('\\"', '"')  # Fix double escaped quotes
            .replace('""', '"')   # Fix double quotes
            .strip())
            
        # Remove any BOM or hidden characters
        cleaned_content = cleaned_content.encode('ascii', 'ignore').decode()
        
        try:
            # First attempt: direct parse
            return json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            # Second attempt: fix common JSON structural issues
            try:
                # Fix missing commas
                if "Expecting ',' delimiter" in str(e):
                    cleaned_content = cleaned_content.replace('} {', '}, {')
                    cleaned_content = cleaned_content.replace('" "', '", "')
                
                # Fix unterminated strings
                if "Unterminated string" in str(e):
                    pos = e.pos
                    # Add missing quote if we can find the property name
                    if pos > 0 and cleaned_content[pos-1] == ':':
                        cleaned_content = cleaned_content[:pos] + '"' + cleaned_content[pos:] + '"'
                
                # Fix missing colons
                if "Expecting ':' delimiter" in str(e):
                    parts = cleaned_content.split('"')
                    for i in range(1, len(parts), 2):
                        if i+1 < len(parts) and not parts[i+1].strip().startswith(':'):
                            parts[i+1] = ':' + parts[i+1]
                    cleaned_content = '"'.join(parts)
                
                return json.loads(cleaned_content)
            except json.JSONDecodeError as final_error:
                logger.warning(f"Final JSON parsing error: {str(final_error)}")
                return None
            
    except Exception as e:
        logger.error(f"Unexpected error parsing analysis: {str(e)}")
        return None
def get_market_details_safely(market: Dict) -> Dict:
    """Safely extract market details with default values."""
    try:
        # Get basic market details
        ticker = market.get('market', 'UNKNOWN')
        volume = process_market_volume(market)
        liquidity = float(market.get('24hr_volume', '0').replace('$', '').replace(',', ''))
        start_date = market.get('start_date')
        end_date = market.get('end_date')
        
        # Extract probability details
        details = market.get('details', [])
        probabilities = []
        for detail in details:
            prob_entry = {
                'question': detail.get('question', ''),
                'outcomes': []
            }
            for prob in detail.get('probabilities', []):
                prob_entry['outcomes'].append({
                    'outcome': prob.get('outcome', ''),
                    'probability': float(prob.get('probability', '0').rstrip('%'))
                })
            probabilities.append(prob_entry)
            
        # Get the analysis if available
        analysis_dict = parse_analysis_safely(market)
        
        return {
            'ticker': ticker,
            'liquidity': liquidity,
            'volume': volume,
            'start_date': start_date,
            'end_date': end_date,
            'probabilities': probabilities,
            'analysis': analysis_dict
        }
    except Exception as e:
        logger.warning(f"Error extracting market details: {str(e)}")
        return {
            'ticker': market.get('market', 'UNKNOWN'),
            'liquidity': 0.0,
            'volume': 0.0,
            'start_date': None,
            'end_date': None,
            'probabilities': [],
            'analysis': None
        }
def build_domain_context(data: Dict, domain: str) -> Dict:
    """Build domain context with enhanced error handling."""
    domain_mapping = {
        'economic': 'economic_indicators',
        'geopolitical': 'geopolitical_events',
        'regulatory': 'regulatory_changes',
        'technological': 'technological_developments'
    }
    
    if domain not in domain_mapping:
        logger.error(f"Invalid domain requested: {domain}")
        return create_empty_context(data.get('timestamp'), domain)
    
    domain_key = domain_mapping[domain]
    domain_markets = []
    
    for market in data.get('results', []):
        try:
            analysis_dict = parse_analysis_safely(market)
            if not analysis_dict:
                continue
                
            domain_info = analysis_dict.get(domain_key, {})
            if not domain_info:
                continue
                
            # Check if we have valid impact and relevance values
            impact = domain_info.get('impact')
            relevance = domain_info.get('relevance', 0)
            
            if impact and isinstance(relevance, (int, float)) and relevance >= 6:
                market_details = get_market_details_safely(market)
                market_data = {
                    'ticker': market_details['ticker'],
                    'relevance_score': relevance,
                    'liquidity': market_details['liquidity'],
                    'volume': market_details['volume'],
                    'start_date': market_details['start_date'],
                    'end_date': market_details['end_date'],
                    'probabilities': market_details['probabilities'],
                    'analysis': {
                        domain_key: domain_info,
                        'full_analysis': market_details['analysis']
                    } if market_details['analysis'] else None
                }
                domain_markets.append(market_data)
                
        except Exception as e:
            logger.warning(f"Error processing market for domain {domain}: {str(e)}")
            continue
    
    return {
        'timestamp': data.get('timestamp', datetime.now().isoformat()),
        'domain': domain,
        'market_count': len(domain_markets),
        'markets': sorted(domain_markets, key=lambda x: x['relevance_score'], reverse=True),
        'status': 'success'
    }

def create_empty_context(timestamp: str, domain: str) -> Dict:
    """Create an empty context structure for invalid or error cases."""
    return {
        'timestamp': timestamp or datetime.now().isoformat(),
        'domain': domain,
        'market_count': 0,
        'markets': [],
        'status': 'error',
        'error': f'Invalid domain or no data available for {domain}'
    }

def save_analysis_results(results: Dict, filename: str):
    """Save processed analysis results to a JSON file."""
    try:
        output_path = f"processed_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        if filename:
            output_path = filename
            
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")

def process_market_volume(market: Dict) -> float:
    """Safely process market volume string to float."""
    try:
        volume_str = market.get('total_volume', '0')
        volume_str = volume_str.replace('$', '').replace(',', '')
        return float(volume_str)
    except (ValueError, TypeError):
        return 0.0

def test_market_processing():
    """Test the market processing with enhanced error handling."""
    try:
        # Read the JSON file
        with open('markets-preAnalyzed/market_analysis_final_20250204_012032.json', 'r') as file:
            data = json.load(file)
        
        logger.info("=== Basic Data Validation ===")
        logger.info(f"Timestamp: {data.get('timestamp', 'Not available')}")
        logger.info(f"Total Markets: {data.get('total_markets', 0)}")
        logger.info(f"Results count: {len(data.get('results', []))}")
        
        # Process first market if available
        results = data.get('results', [])
        if results:
            first_market = results[0]
            market_details = get_market_details_safely(first_market)
            
            logger.info("\n=== First Market Details ===")
            logger.info(f"Ticker: {market_details['ticker']}")
            logger.info(f"Liquidity: {market_details['liquidity']}")
            logger.info(f"Volume: {market_details['volume']}")
            
            # Test analysis extraction
            analysis_dict = parse_analysis_safely(first_market)
            if analysis_dict:
                logger.info("\n=== Analysis Content ===")
                for domain, info in analysis_dict.items():
                    logger.info(f"\n{domain}:")
                    logger.info(f"Impact: {info.get('impact')}")
                    logger.info(f"Relevance: {info.get('relevance')}")
                    reasoning = info.get('reasoning', '')
                    logger.info(f"Reasoning: {reasoning[:100]}..." if reasoning else "No reasoning provided")
        
        # Test domain context building
        logger.info("\n=== Testing Domain Context Building ===")
        domains = ['economic', 'geopolitical', 'regulatory', 'technological']
        
        # Create results structure
        analysis_results = {
            'timestamp': data.get('timestamp'),
            'total_markets': data.get('total_markets'),
            'domain_analysis': {},
            'market_statistics': {
                'total_volume': sum(process_market_volume(m) for m in results),
                'active_markets': len(results),
                'high_relevance_markets': 0  # Will be updated while processing domains
            }
        }
        
        for domain in domains:
            context = build_domain_context(data, domain)
            logger.info(f"\nDomain: {domain}")
            logger.info(f"Status: {context.get('status', 'unknown')}")
            logger.info(f"Relevant markets found: {context['market_count']}")
            
            # Add domain results to output
            analysis_results['domain_analysis'][domain] = {
                'market_count': context['market_count'],
                'relevant_markets': [
                    {
                        'ticker': m['ticker'],
                        'relevance_score': m['relevance_score'],
                        'liquidity': m['liquidity'],
                        'volume': m['volume']
                    }
                    for m in context['markets'][:10]  # Top 10 most relevant markets
                ]
            }
            
            # Update high relevance market count
            analysis_results['market_statistics']['high_relevance_markets'] += sum(
                1 for m in context['markets'] if m['relevance_score'] >= 8
            )
            
            if context['markets']:
                top_market = context['markets'][0]
                logger.info(f"Top market ticker: {top_market['ticker']}")
                logger.info(f"Top market relevance: {top_market['relevance_score']}")
        
        # Save the processed results
        save_analysis_results(analysis_results, 'market_analysis_processed.json')
                
    except FileNotFoundError:
        logger.error("Market analysis file not found")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        logger.error("\nFull traceback:")
        logger.error(traceback.format_exc())

def build_domain_context(data: Dict, domain: str) -> Dict:
    """Build domain context with enhanced error handling."""
    domain_mapping = {
        'economic': 'economic_indicators',
        'geopolitical': 'geopolitical_events',
        'regulatory': 'regulatory_changes',
        'technological': 'technological_developments'
    }
    
    if domain not in domain_mapping:
        logger.error(f"Invalid domain requested: {domain}")
        return create_empty_context(data.get('timestamp'), domain)
    
    domain_key = domain_mapping[domain]
    domain_markets = []
    
    for market in data.get('results', []):
        try:
            analysis_dict = parse_analysis_safely(market)
            if not analysis_dict:
                continue
                
            domain_info = analysis_dict.get(domain_key, {})
            if not domain_info:
                continue
                
            # Check if we have valid impact and relevance values
            impact = domain_info.get('impact')
            relevance = domain_info.get('relevance', 0)
            
            if impact and isinstance(relevance, (int, float)) and relevance >= 6:
                market_details = get_market_details_safely(market)
                market_data = {
                    'ticker': market_details['ticker'],
                    'relevance_score': relevance,
                    'liquidity': market_details['liquidity'],
                    'volume': market_details['volume']
                }
                domain_markets.append(market_data)
                
        except Exception as e:
            logger.warning(f"Error processing market for domain {domain}: {str(e)}")
            continue
    
    return {
        'timestamp': data.get('timestamp', datetime.now().isoformat()),
        'domain': domain,
        'market_count': len(domain_markets),
        'markets': sorted(domain_markets, key=lambda x: x['relevance_score'], reverse=True),
        'status': 'success'
    }

def create_empty_context(timestamp: str, domain: str) -> Dict:
    """Create an empty context structure for invalid or error cases."""
    return {
        'timestamp': timestamp or datetime.now().isoformat(),
        'domain': domain,
        'market_count': 0,
        'markets': [],
        'status': 'error',
        'error': f'Invalid domain or no data available for {domain}'
    }

def save_analysis_results(results: Dict, filename: str):
    """Save processed analysis results to a JSON file."""
    try:
        output_path = f"processed_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        if filename:
            output_path = filename
            
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")

def process_market_volume(market: Dict) -> float:
    """Safely process market volume string to float."""
    try:
        volume_str = market.get('total_volume', '0')
        volume_str = volume_str.replace('$', '').replace(',', '')
        return float(volume_str)
    except (ValueError, TypeError):
        return 0.0

def test_market_processing():
    """Test the market processing with enhanced error handling."""
    try:
        # Read the JSON file
        with open('markets-preAnalyzed/market_analysis_final_20250204_012032.json', 'r') as file:
            data = json.load(file)
        
        logger.info("=== Basic Data Validation ===")
        logger.info(f"Timestamp: {data.get('timestamp', 'Not available')}")
        logger.info(f"Total Markets: {data.get('total_markets', 0)}")
        logger.info(f"Results count: {len(data.get('results', []))}")
        
        # Process first market if available
        results = data.get('results', [])
        if results:
            first_market = results[0]
            market_details = get_market_details_safely(first_market)
            
            logger.info("\n=== First Market Details ===")
            logger.info(f"Ticker: {market_details['ticker']}")
            logger.info(f"Liquidity: {market_details['liquidity']}")
            logger.info(f"Volume: {market_details['volume']}")
            
            # Test analysis extraction
            analysis_dict = parse_analysis_safely(first_market)
            if analysis_dict:
                logger.info("\n=== Analysis Content ===")
                for domain, info in analysis_dict.items():
                    logger.info(f"\n{domain}:")
                    logger.info(f"Impact: {info.get('impact')}")
                    logger.info(f"Relevance: {info.get('relevance')}")
                    reasoning = info.get('reasoning', '')
                    logger.info(f"Reasoning: {reasoning[:100]}..." if reasoning else "No reasoning provided")
        
        # Test domain context building
        logger.info("\n=== Testing Domain Context Building ===")
        domains = ['economic', 'geopolitical', 'regulatory', 'technological']
        
        # Create results structure
        analysis_results = {
            'timestamp': data.get('timestamp'),
            'total_markets': data.get('total_markets'),
            'domain_analysis': {},
            'market_statistics': {
                'total_volume': sum(process_market_volume(m) for m in results),
                'active_markets': len(results),
                'high_relevance_markets': 0  # Will be updated while processing domains
            }
        }
        
        for domain in domains:
            context = build_domain_context(data, domain)
            logger.info(f"\nDomain: {domain}")
            logger.info(f"Status: {context.get('status', 'unknown')}")
            logger.info(f"Relevant markets found: {context['market_count']}")
            
            # Add domain results to output
            analysis_results['domain_analysis'][domain] = {
                'market_count': context['market_count'],
                'relevant_markets': [
                    {
                        'ticker': m['ticker'],
                        'relevance_score': m['relevance_score'],
                        'liquidity': m['liquidity'],
                        'volume': m['volume']
                    }
                    for m in context['markets'][:10]  # Top 10 most relevant markets
                ]
            }
            
            # Update high relevance market count
            analysis_results['market_statistics']['high_relevance_markets'] += sum(
                1 for m in context['markets'] if m['relevance_score'] >= 8
            )
            
            if context['markets']:
                top_market = context['markets'][0]
                logger.info(f"Top market ticker: {top_market['ticker']}")
                logger.info(f"Top market relevance: {top_market['relevance_score']}")
        
        # Save the processed results
        save_analysis_results(analysis_results, 'market_analysis_processed.json')
                
    except FileNotFoundError:
        logger.error("Market analysis file not found")
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        logger.error("\nFull traceback:")
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    logger.info("Starting market data processing test...")
    test_market_processing()