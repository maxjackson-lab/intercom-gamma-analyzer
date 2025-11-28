import argparse
import re
from pathlib import Path
from typing import List, Dict, Any
import sys

def analyze_sentiment_quality(log_file_path: str) -> Dict[str, Any]:
    """
    Analyze sentiment quality from a log file.
    
    Args:
        log_file_path: Path to the log file
        
    Returns:
        Dictionary with summary statistics
    """
    path = Path(log_file_path)
    if not path.exists():
        print(f"Error: Log file not found: {log_file_path}")
        return {}

    content = path.read_text(encoding='utf-8')
    
    # Extract insights using regex assuming standard log format
    # Pattern looks for: "Insight: <text>"
    # This matches the logger.info(f"   Insight: {insight}") in TopicSentimentAgent
    insight_pattern = re.compile(r"Insight:\s+(.+)$", re.MULTILINE)
    insights = insight_pattern.findall(content)
    
    if not insights:
        print(f"No sentiment insights found in {log_file_path}")
        return {}

    stats = {
        'total_insights': len(insights),
        'insights_with_nuance': 0,
        'insights_with_generic_patterns': 0,
        'total_quality_score': 0.0,
        'average_length': 0.0,
        'details': []
    }
    
    nuance_connectors = ["but", "however", "although", "yet"]
    bad_patterns = [
        'negative sentiment', 'positive sentiment', 'mixed sentiment',
        'users are frustrated', 'customers express', 'sentiment detected',
        'sentiment about', 'have issues', 'have problems'
    ]
    
    total_chars = 0
    
    for insight in insights:
        insight_lower = insight.lower()
        
        # Check nuance
        has_nuance = any(c in insight_lower for c in nuance_connectors)
        if has_nuance:
            stats['insights_with_nuance'] += 1
            
        # Check generic patterns
        has_generic = any(p in insight_lower for p in bad_patterns)
        if has_generic:
            stats['insights_with_generic_patterns'] += 1
            
        # Length
        length = len(insight)
        total_chars += length
        
        # Calculate score (simplified version of agent logic)
        score = 1.0
        if not has_nuance:
            score -= 0.2
        if has_generic:
            score -= 0.3
        if length < 20:
            score -= 0.1
        if length > 200:
            score -= 0.1
        score = max(0.0, score)
        
        stats['total_quality_score'] += score
        
        stats['details'].append({
            'insight': insight,
            'score': round(score, 2),
            'has_nuance': has_nuance,
            'has_generic': has_generic
        })

    stats['average_quality_score'] = stats['total_quality_score'] / len(insights)
    stats['average_length'] = total_chars / len(insights)
    
    return stats

def print_report(stats: Dict[str, Any]):
    """Print markdown report"""
    if not stats:
        return

    print("\n# Sentiment Quality Analysis Report")
    print("===================================\n")
    
    print("## Summary Statistics")
    print(f"- **Total Insights Analyzed:** {stats['total_insights']}")
    print(f"- **Average Quality Score:** {stats['average_quality_score']:.2f} / 1.0")
    print(f"- **Insights with Nuance:** {stats['insights_with_nuance']} ({stats['insights_with_nuance']/stats['total_insights']*100:.1f}%)")
    print(f"- **Insights with Generic Patterns:** {stats['insights_with_generic_patterns']} ({stats['insights_with_generic_patterns']/stats['total_insights']*100:.1f}%)")
    print(f"- **Average Length:** {stats['average_length']:.1f} characters\n")
    
    print("## Detailed Insights (Lowest Quality First)\n")
    
    # Sort by score ascending
    sorted_details = sorted(stats['details'], key=lambda x: x['score'])
    
    for detail in sorted_details:
        status = "✅" if detail['score'] >= 0.8 else "⚠️" if detail['score'] >= 0.5 else "❌"
        print(f"### {status} Score: {detail['score']}")
        print(f"> {detail['insight']}")
        print(f"- Nuance: {'Yes' if detail['has_nuance'] else 'No'}")
        print(f"- Generic: {'Yes' if detail['has_generic'] else 'No'}\n")

def main():
    parser = argparse.ArgumentParser(description="Validate sentiment quality from log files.")
    parser.add_argument("--log-file", help="Path to a specific log file to analyze")
    parser.add_argument("--log-dir", help="Directory to scan for latest log file")
    
    args = parser.parse_args()
    
    target_file = None
    
    if args.log_file:
        target_file = args.log_file
    elif args.log_dir:
        # Find latest .log file in directory
        log_dir = Path(args.log_dir)
        if log_dir.exists() and log_dir.is_dir():
            logs = list(log_dir.glob("*.log"))
            if logs:
                target_file = str(max(logs, key=lambda p: p.stat().st_mtime))
                print(f"Analyzing latest log file: {target_file}")
            else:
                print(f"No .log files found in {args.log_dir}")
                return
    else:
        # Default to outputs/ directory
        log_dir = Path("outputs")
        if log_dir.exists():
             logs = list(log_dir.glob("*.log"))
             if logs:
                target_file = str(max(logs, key=lambda p: p.stat().st_mtime))
                print(f"Analyzing latest log file: {target_file}")
    
    if target_file:
        stats = analyze_sentiment_quality(target_file)
        print_report(stats)
    else:
        print("No log file specified or found. Use --log-file or ensure 'outputs/' has logs.")

if __name__ == "__main__":
    main()


