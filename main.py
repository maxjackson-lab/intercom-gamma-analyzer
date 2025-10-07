"""
Main execution script for Intercom trend analysis.
"""

import os
import sys
import logging
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv
from tqdm import tqdm

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from intercom_client import IntercomClient, IntercomAPIError
from text_analyzer import TextAnalyzer
from trend_analyzer import TrendAnalyzer
from report_generator import ReportGenerator

# Load environment variables
load_dotenv()

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('intercom_analysis.log')
        ]
    )

def validate_environment():
    """Validate required environment variables."""
    access_token = os.getenv('INTERCOM_ACCESS_TOKEN')
    if not access_token:
        raise ValueError(
            "INTERCOM_ACCESS_TOKEN environment variable is required. "
            "Please set it in your .env file or environment."
        )
    return access_token

def create_progress_callback(total: int):
    """Create progress callback for tqdm."""
    pbar = tqdm(total=total, desc="Processing conversations", unit="conv")
    
    def callback(processed: int, total_conversations: int):
        pbar.update(processed - pbar.n)
        if processed >= total_conversations:
            pbar.close()
    
    return callback

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Intercom Conversation Trend Analyzer')
    parser.add_argument('--days', type=int, default=180, 
                       help='Number of days to analyze (default: 180)')
    parser.add_argument('--max-pages', type=int, default=None,
                       help='Maximum number of pages to fetch (for testing)')
    parser.add_argument('--patterns', nargs='+', 
                       default=['cache', 'browser', 'extension', 'slow', 'loading', 
                               'cookies', 'incognito', 'firewall', 'network', 'error'],
                       help='Patterns to search for in conversations')
    parser.add_argument('--output-dir', default='outputs',
                       help='Output directory for reports (default: outputs)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--text-search', type=str, default=None,
                       help='Search for conversations containing specific text')
    parser.add_argument('--include-details', action='store_true', default=True,
                       help='Include detailed analysis in reports')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Validate environment
        access_token = validate_environment()
        logger.info("Environment validation successful")
        
        # Initialize clients
        logger.info("Initializing Intercom client...")
        intercom_client = IntercomClient(access_token=access_token)
        
        logger.info("Initializing text analyzer...")
        text_analyzer = TextAnalyzer()
        
        # Define date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
        
        logger.info(f"Analysis period: {start_date.date()} to {end_date.date()} ({args.days} days)")
        
        # Create query
        if args.text_search:
            logger.info(f"Searching for conversations containing: '{args.text_search}'")
            query = intercom_client.create_text_search_query(
                args.text_search,
                intercom_client.create_date_range_query(start_date, end_date)
            )
        else:
            query = intercom_client.create_date_range_query(start_date, end_date)
        
        # Get conversation count first
        logger.info("Getting conversation count...")
        try:
            total_count = intercom_client.get_conversation_count(query)
            logger.info(f"Found {total_count:,} conversations matching query")
        except IntercomAPIError as e:
            logger.warning(f"Could not get conversation count: {e}")
            total_count = "unknown"
        
        # Fetch conversations
        logger.info("Starting conversation fetch...")
        conversations = list(intercom_client.search_conversations(
            query=query, 
            max_pages=args.max_pages
        ))
        
        logger.info(f"Fetched {len(conversations):,} conversations")
        
        if not conversations:
            logger.warning("No conversations found matching the criteria")
            return
        
        # Create progress callback
        progress_callback = create_progress_callback(len(conversations))
        
        # Perform text analysis
        logger.info("Performing keyword extraction...")
        text_results = text_analyzer.analyze_conversations(
            conversations, 
            progress_callback=progress_callback
        )
        
        # Perform trend analysis
        logger.info("Analyzing trends...")
        
        # Pattern analysis
        pattern_counts = TrendAnalyzer.pattern_analysis(conversations, args.patterns)
        
        # State and source analysis
        state_breakdown = TrendAnalyzer.conversations_by_state(conversations)
        source_breakdown = TrendAnalyzer.conversations_by_source_type(conversations)
        
        # Time-based analysis
        conversations_by_date = TrendAnalyzer.conversations_by_date(conversations)
        conversations_by_hour = TrendAnalyzer.conversations_by_hour(conversations)
        weekly_trends = TrendAnalyzer.weekly_trends(conversations)
        
        # Agent analysis
        agent_analysis = TrendAnalyzer.agent_response_analysis(conversations)
        
        # Length and response time analysis
        conversation_length = TrendAnalyzer.conversation_length_analysis(conversations)
        response_time = TrendAnalyzer.response_time_analysis(conversations)
        
        # Customer satisfaction analysis
        satisfaction_analysis = TrendAnalyzer.customer_satisfaction_analysis(conversations)
        
        # Combine results
        analysis_results = {
            **text_results,
            'pattern_counts': pattern_counts,
            'state_breakdown': state_breakdown,
            'source_breakdown': source_breakdown,
            'conversations_by_date': conversations_by_date,
            'conversations_by_hour': conversations_by_hour,
            'weekly_trends': weekly_trends,
            'agent_analysis': agent_analysis,
            'conversation_length': conversation_length,
            'response_time': response_time,
            'satisfaction_analysis': satisfaction_analysis,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': args.days
            },
            'query_info': {
                'text_search': args.text_search,
                'patterns_searched': args.patterns,
                'max_pages': args.max_pages
            }
        }
        
        # Generate reports
        logger.info(f"Generating reports in {args.output_dir}...")
        ReportGenerator.generate_all_reports(
            analysis_results,
            args.output_dir,
            include_details=args.include_details
        )
        
        # Print summary
        print("\n" + "="*80)
        print("ANALYSIS COMPLETE!")
        print("="*80)
        print(f"📊 Total Conversations: {len(conversations):,}")
        print(f"🔑 Unique Keywords: {text_results.get('unique_keywords', 0):,}")
        print(f"📁 Reports saved to: {args.output_dir}/")
        print("\nGenerated files:")
        print(f"  • trend_report.txt - Detailed analysis report")
        print(f"  • summary.txt - Quick summary")
        print(f"  • trend_report.json - Full data (JSON)")
        print(f"  • *.csv files - Data for Excel analysis")
        print("="*80)
        
        # Show top keywords
        if text_results.get('top_keywords'):
            print("\n🏆 Top 5 Keywords:")
            for i, (keyword, count) in enumerate(text_results['top_keywords'][:5], 1):
                percentage = (count / len(conversations)) * 100
                print(f"  {i}. {keyword} ({count}, {percentage:.1f}%)")
        
        # Show top patterns
        if pattern_counts:
            print("\n🎯 Top Patterns Found:")
            sorted_patterns = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)
            for i, (pattern, count) in enumerate(sorted_patterns[:5], 1):
                percentage = (count / len(conversations)) * 100
                print(f"  {i}. {pattern} ({count}, {percentage:.1f}%)")
        
        logger.info("Analysis completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()


