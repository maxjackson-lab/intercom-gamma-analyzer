"""
Railway cron job entrypoint for Intercom Analysis Tool.
Designed for scheduled execution on Railway.app platform.
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from main import run_comprehensive_analysis_wrapper

def run_weekly_analysis():
    """Run weekly analysis for the past 7 days."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    print(f"🚀 Starting weekly analysis: {start_date_str} to {end_date_str}")
    
    result = run_comprehensive_analysis_wrapper(
        start_date=start_date_str,
        end_date=end_date_str,
        max_conversations=2000,
        generate_gamma=True,
        gamma_style="executive",
        gamma_export="pdf",
        export_docs=True
    )
    
    if result.get('success'):
        print(f"✅ Weekly analysis completed successfully!")
        if result.get('gamma_url'):
            print(f"📊 Gamma URL: {result['gamma_url']}")
        if result.get('export_url'):
            print(f"📄 Export URL: {result['export_url']}")
        print(f"💳 Credits used: {result.get('credits_used', 'N/A')}")
    else:
        print(f"❌ Weekly analysis failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

def run_monthly_analysis():
    """Run monthly analysis for the past 30 days."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    print(f"🚀 Starting monthly analysis: {start_date_str} to {end_date_str}")
    
    result = run_comprehensive_analysis_wrapper(
        start_date=start_date_str,
        end_date=end_date_str,
        max_conversations=5000,
        generate_gamma=True,
        gamma_style="detailed",
        gamma_export="pptx",
        export_docs=True
    )
    
    if result.get('success'):
        print(f"✅ Monthly analysis completed successfully!")
        if result.get('gamma_url'):
            print(f"📊 Gamma URL: {result['gamma_url']}")
        if result.get('export_url'):
            print(f"📄 Export URL: {result['export_url']}")
        print(f"💳 Credits used: {result.get('credits_used', 'N/A')}")
    else:
        print(f"❌ Monthly analysis failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

def run_custom_analysis():
    """Run custom analysis based on environment variables."""
    # Get parameters from environment variables
    start_date = os.getenv('ANALYSIS_START_DATE')
    end_date = os.getenv('ANALYSIS_END_DATE')
    max_conversations = int(os.getenv('MAX_CONVERSATIONS', '1000'))
    gamma_style = os.getenv('GAMMA_STYLE', 'executive')
    gamma_export = os.getenv('GAMMA_EXPORT')
    
    if not start_date or not end_date:
        print("❌ ANALYSIS_START_DATE and ANALYSIS_END_DATE environment variables are required")
        sys.exit(1)
    
    print(f"🚀 Starting custom analysis: {start_date} to {end_date}")
    
    result = run_comprehensive_analysis_wrapper(
        start_date=start_date,
        end_date=end_date,
        max_conversations=max_conversations,
        generate_gamma=True,
        gamma_style=gamma_style,
        gamma_export=gamma_export,
        export_docs=True
    )
    
    if result.get('success'):
        print(f"✅ Custom analysis completed successfully!")
        if result.get('gamma_url'):
            print(f"📊 Gamma URL: {result['gamma_url']}")
        if result.get('export_url'):
            print(f"📄 Export URL: {result['export_url']}")
        print(f"💳 Credits used: {result.get('credits_used', 'N/A')}")
    else:
        print(f"❌ Custom analysis failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

def main():
    """Main entrypoint for Railway cron jobs."""
    analysis_type = os.getenv('ANALYSIS_TYPE', 'weekly')
    
    print(f"🕐 Railway cron job started at {datetime.now().isoformat()}")
    print(f"📋 Analysis type: {analysis_type}")
    
    try:
        if analysis_type == 'weekly':
            run_weekly_analysis()
        elif analysis_type == 'monthly':
            run_monthly_analysis()
        elif analysis_type == 'custom':
            run_custom_analysis()
        else:
            print(f"❌ Unknown analysis type: {analysis_type}")
            print("Valid types: weekly, monthly, custom")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Analysis failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print(f"🏁 Railway cron job completed at {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()




