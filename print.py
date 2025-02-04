import json
import sys
from datetime import datetime
from typing import Dict, Any, List
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init()

class MarketAnalysisViewer:
    def __init__(self, filename: str):
        self.filename = filename
        self.data = self.load_data()

    def load_data(self) -> List[Dict[str, Any]]:
        """Load the JSON data from file"""
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"{Fore.RED}Error: File {self.filename} not found{Style.RESET_ALL}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"{Fore.RED}Error: Invalid JSON format in {self.filename}{Style.RESET_ALL}")
            sys.exit(1)

    def parse_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the analysis response from the API"""
        try:
            # Extract the response content from the API response
            response = analysis.get('choices', [{}])[0].get('message', {}).get('content', '{}')
            return json.loads(response)
        except (json.JSONDecodeError, KeyError):
            return {}

    def format_impact_section(self, section_data: Dict[str, Any]) -> str:
        """Format a single impact section"""
        impact = "Yes" if section_data.get('impact', False) else "No"
        relevance = section_data.get('relevance', 0)
        reasoning = section_data.get('reasoning', 'No reasoning provided')

        # Color code based on relevance score
        if relevance >= 7:
            color = Fore.RED
        elif relevance >= 4:
            color = Fore.YELLOW
        else:
            color = Fore.GREEN

        return f"""    Impact: {color}{impact}{Style.RESET_ALL}
    Relevance: {color}{relevance}/10{Style.RESET_ALL}
    Reasoning: {reasoning}"""

    def display_market_analysis(self):
        """Display the market analysis results in a formatted way"""
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}Market Analysis Results - Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}\n{Style.RESET_ALL}")

        for i, result in enumerate(self.data, 1):
            ticker = result.get('ticker', 'Unknown Market')
            analysis = result.get('analysis', {})
            
            # Parse the analysis response
            parsed_analysis = self.parse_analysis(analysis)
            
            print(f"{Fore.BLUE}Market {i}/{len(self.data)}: {ticker}{Style.RESET_ALL}")
            print(f"{'-'*40}")
            
            if not parsed_analysis:
                print(f"{Fore.RED}No valid analysis data available{Style.RESET_ALL}\n")
                continue

            # Display each impact area
            for area in ['economic_indicators', 'geopolitical_events', 
                        'regulatory_changes', 'technological_developments']:
                if area in parsed_analysis:
                    print(f"\n{area.replace('_', ' ').title()}:")
                    print(self.format_impact_section(parsed_analysis[area]))

            print(f"\n{Fore.BLUE}{'='*40}{Style.RESET_ALL}\n")

    def print_summary(self):
        """Print summary statistics of the analysis"""
        total_markets = len(self.data)
        
        # Count markets with valid analyses
        valid_analyses = sum(1 for r in self.data if self.parse_analysis(r.get('analysis', {})))
        
        print(f"\n{Fore.CYAN}Analysis Summary:{Style.RESET_ALL}")
        print(f"Total Markets Analyzed: {total_markets}")
        print(f"Valid Analyses: {valid_analyses}")
        print(f"Success Rate: {(valid_analyses/total_markets)*100:.1f}%")

def main():
    if len(sys.argv) != 2:
        print(f"{Fore.RED}Usage: python view_analysis.py <analysis_file.json>{Style.RESET_ALL}")
        sys.exit(1)

    viewer = MarketAnalysisViewer(sys.argv[1])
    viewer.display_market_analysis()
    viewer.print_summary()

if __name__ == "__main__":
    main()