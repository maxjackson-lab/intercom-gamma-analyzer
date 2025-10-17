"""
Modal Labs deployment for Intercom Analysis Tool.
Provides scheduled and on-demand analysis functions.
"""

import modal
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Create Modal app
app = modal.App("intercom-analysis-tool")

# Define the image with all dependencies
image = modal.Image.debian_slim(python_version="3.11").pip_install([
    "click",
    "rich",
    "pydantic",
    "structlog",
    "openai",
    "duckdb",
    "pandas",
    "beautifulsoup4",
    "lxml",
    "tenacity",
    "PyYAML",
    "httpx",
    "aiohttp"
]).env({
    "INTERCOM_ACCESS_TOKEN": os.getenv("INTERCOM_ACCESS_TOKEN"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "GAMMA_API_KEY": os.getenv("GAMMA_API_KEY"),
    "INTERCOM_WORKSPACE_ID": os.getenv("INTERCOM_WORKSPACE_ID")
})

# Mount the source code
app = app.mount_local_dir("/Users/max.jackson/Intercom Analysis Tool /src", remote_path="/src")

@app.function(
    image=image,
    timeout=3600,  # 1 hour timeout
    memory=2048,   # 2GB memory
    cpu=2,         # 2 CPU cores
    secrets=[
        modal.Secret.from_name("intercom-analysis-secrets")
    ]
)
def run_weekly_analysis() -> Dict[str, Any]:
    """
    Scheduled weekly analysis function.
    Runs every Monday at 9 AM UTC.
    """
    import sys
    sys.path.append("/src")
    
    from main import run_comprehensive_analysis_wrapper
    
    # Calculate date range (last 7 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    print(f"Running weekly analysis for {start_date_str} to {end_date_str}")
    
    result = run_comprehensive_analysis_wrapper(
        start_date=start_date_str,
        end_date=end_date_str,
        max_conversations=2000,
        generate_gamma=True,
        gamma_style="executive",
        gamma_export="pdf",
        export_docs=True
    )
    
    print(f"Weekly analysis completed: {result.get('success', False)}")
    if result.get('gamma_url'):
        print(f"Gamma URL: {result['gamma_url']}")
    
    return result

@app.function(
    image=image,
    timeout=3600,  # 1 hour timeout
    memory=2048,   # 2GB memory
    cpu=2,         # 2 CPU cores
    secrets=[
        modal.Secret.from_name("intercom-analysis-secrets")
    ]
)
def run_monthly_analysis() -> Dict[str, Any]:
    """
    Scheduled monthly analysis function.
    Runs on the 1st of every month at 9 AM UTC.
    """
    import sys
    sys.path.append("/src")
    
    from main import run_comprehensive_analysis_wrapper
    
    # Calculate date range (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')
    
    print(f"Running monthly analysis for {start_date_str} to {end_date_str}")
    
    result = run_comprehensive_analysis_wrapper(
        start_date=start_date_str,
        end_date=end_date_str,
        max_conversations=5000,
        generate_gamma=True,
        gamma_style="detailed",
        gamma_export="pptx",
        export_docs=True
    )
    
    print(f"Monthly analysis completed: {result.get('success', False)}")
    if result.get('gamma_url'):
        print(f"Gamma URL: {result['gamma_url']}")
    
    return result

@app.function(
    image=image,
    timeout=3600,  # 1 hour timeout
    memory=2048,   # 2GB memory
    cpu=2,         # 2 CPU cores
    secrets=[
        modal.Secret.from_name("intercom-analysis-secrets")
    ]
)
def run_custom_analysis(
    start_date: str,
    end_date: str,
    max_conversations: int = 1000,
    gamma_style: str = "executive",
    gamma_export: Optional[str] = None
) -> Dict[str, Any]:
    """
    On-demand analysis function for custom date ranges.
    """
    import sys
    sys.path.append("/src")
    
    from main import run_comprehensive_analysis_wrapper
    
    print(f"Running custom analysis for {start_date} to {end_date}")
    
    result = run_comprehensive_analysis_wrapper(
        start_date=start_date,
        end_date=end_date,
        max_conversations=max_conversations,
        generate_gamma=True,
        gamma_style=gamma_style,
        gamma_export=gamma_export,
        export_docs=True
    )
    
    print(f"Custom analysis completed: {result.get('success', False)}")
    if result.get('gamma_url'):
        print(f"Gamma URL: {result['gamma_url']}")
    
    return result

# Scheduled functions
@app.function(
    image=image,
    schedule=modal.Cron("0 9 * * 1"),  # Every Monday at 9 AM UTC
    timeout=3600,
    memory=2048,
    cpu=2,
    secrets=[
        modal.Secret.from_name("intercom-analysis-secrets")
    ]
)
def scheduled_weekly_analysis():
    """Scheduled weekly analysis - runs automatically."""
    return run_weekly_analysis.remote()

@app.function(
    image=image,
    schedule=modal.Cron("0 9 1 * *"),  # 1st of every month at 9 AM UTC
    timeout=3600,
    memory=2048,
    cpu=2,
    secrets=[
        modal.Secret.from_name("intercom-analysis-secrets")
    ]
)
def scheduled_monthly_analysis():
    """Scheduled monthly analysis - runs automatically."""
    return run_monthly_analysis.remote()

# Local development functions
@app.local_entrypoint()
def main():
    """Local entrypoint for testing."""
    print("Intercom Analysis Tool - Modal Deployment")
    print("Available functions:")
    print("1. run_weekly_analysis()")
    print("2. run_monthly_analysis()")
    print("3. run_custom_analysis(start_date, end_date, ...)")
    print("\nTo run a function, use: modal run deploy/modal_app.py::function_name")

if __name__ == "__main__":
    main()




