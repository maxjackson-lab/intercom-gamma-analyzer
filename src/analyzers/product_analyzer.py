"""
Product Analyzer for Intercom Analysis Tool.
Specialized analyzer for product-related conversations including export issues, bugs, and feature requests.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from collections import Counter

from src.analyzers.base_category_analyzer import BaseCategoryAnalyzer, AnalysisError
from src.config.prompts import PromptTemplates
from src.utils.time_utils import to_utc_datetime, ensure_date, calculate_time_delta_seconds

logger = logging.getLogger(__name__)


class ProductAnalyzer(BaseCategoryAnalyzer):
    """
    Specialized analyzer for product-related conversations.
    
    Focuses on:
    - Export functionality issues
    - Product bugs and errors
    - Feature requests and suggestions
    - Product usage questions
    - Technical product problems
    """
    
    def __init__(self, **kwargs):
        """Initialize product analyzer."""
        super().__init__(category_name="Product Question", **kwargs)
        
        # Product-specific patterns
        self.export_patterns = [
            r'export', r'download', r'csv', r'excel', r'data.*export',
            r'export.*data', r'download.*data', r'export.*file'
        ]
        
        self.bug_patterns = [
            r'bug', r'error', r'broken', r'not working', r'issue', r'problem',
            r'glitch', r'fault', r'malfunction', r'defect'
        ]
        
        self.feature_patterns = [
            r'feature.*request', r'add.*feature', r'new.*feature', r'suggestion',
            r'enhancement', r'improvement', r'wish', r'would like'
        ]
        
        self.usage_patterns = [
            r'how.*to', r'how do', r'tutorial', r'guide', r'help.*with',
            r'question.*about', r'how.*use', r'how.*work'
        ]
        
        # Product keywords for classification
        self.product_keywords = {
            'export': ['export', 'download', 'csv', 'excel', 'data export', 'export data'],
            'bug': ['bug', 'error', 'broken', 'not working', 'issue', 'problem', 'glitch'],
            'feature': ['feature', 'request', 'add', 'new', 'suggestion', 'enhancement'],
            'usage': ['how to', 'tutorial', 'guide', 'help', 'question', 'how use'],
            'technical': ['technical', 'api', 'integration', 'connection', 'authentication']
        }
        
        # Export-specific keywords
        self.export_keywords = {
            'csv_export': ['csv', 'comma separated', 'spreadsheet'],
            'excel_export': ['excel', 'xlsx', 'workbook'],
            'data_export': ['data export', 'export data', 'download data'],
            'report_export': ['report', 'export report', 'download report'],
            'bulk_export': ['bulk', 'mass export', 'large export']
        }
        
        # Bug severity indicators
        self.bug_severity_keywords = {
            'critical': ['critical', 'urgent', 'blocking', 'cannot work', 'completely broken'],
            'high': ['major', 'important', 'significant', 'serious'],
            'medium': ['moderate', 'minor', 'inconvenience'],
            'low': ['cosmetic', 'minor', 'small', 'trivial']
        }
        
        self.logger.info("Initialized ProductAnalyzer with specialized product patterns")
    
    async def _perform_category_analysis(
        self, 
        conversations: List[Dict[str, Any]], 
        start_date: datetime, 
        end_date: datetime,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform product-specific analysis.
        
        Args:
            conversations: Filtered product conversations
            start_date: Analysis start date
            end_date: Analysis end date
            options: Analysis options
            
        Returns:
            Product-specific analysis results
        """
        self.logger.info(f"Performing product analysis on {len(conversations)} conversations")
        
        try:
            # Classify conversations by product type
            classified_conversations = self._classify_product_conversations(conversations)
            
            # Analyze export issues
            export_analysis = self._analyze_export_issues(classified_conversations['export'])
            
            # Analyze product bugs
            bug_analysis = self._analyze_product_bugs(classified_conversations['bug'])
            
            # Analyze feature requests
            feature_analysis = self._analyze_feature_requests(classified_conversations['feature'])
            
            # Analyze usage questions
            usage_analysis = self._analyze_usage_questions(classified_conversations['usage'])
            
            # Analyze technical issues
            technical_analysis = self._analyze_technical_issues(classified_conversations['technical'])
            
            # Calculate product metrics
            product_metrics = self._calculate_product_metrics(conversations, classified_conversations)
            
            # Identify product trends
            product_trends = self._identify_product_trends(conversations, start_date, end_date)
            
            # Find common product issues
            common_issues = self._identify_common_product_issues(conversations)
            
            # Analyze product satisfaction
            product_satisfaction = self._analyze_product_satisfaction(conversations)
            
            # Identify macro opportunities
            macro_opportunities = self._identify_macro_opportunities(conversations)
            
            return {
                "analysis_type": "product_analysis",
                "conversation_count": len(conversations),
                "classified_conversations": {
                    category: len(convs) for category, convs in classified_conversations.items()
                },
                "export_analysis": export_analysis,
                "bug_analysis": bug_analysis,
                "feature_analysis": feature_analysis,
                "usage_analysis": usage_analysis,
                "technical_analysis": technical_analysis,
                "product_metrics": product_metrics,
                "product_trends": product_trends,
                "common_issues": common_issues,
                "product_satisfaction": product_satisfaction,
                "macro_opportunities": macro_opportunities
            }
            
        except Exception as e:
            self.logger.error(f"Product analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"Failed to perform product analysis: {e}") from e
    
    def _classify_product_conversations(self, conversations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Classify conversations by product type."""
        classified = {
            'export': [],
            'bug': [],
            'feature': [],
            'usage': [],
            'technical': [],
            'other': []
        }
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            classified_into = False
            
            # Check each product type
            for product_type, keywords in self.product_keywords.items():
                if any(keyword in text for keyword in keywords):
                    classified[product_type].append(conv)
                    conv['product_type'] = product_type
                    classified_into = True
                    break
            
            if not classified_into:
                classified['other'].append(conv)
                conv['product_type'] = 'other'
        
        self.logger.info(f"Classified conversations: {[(k, len(v)) for k, v in classified.items()]}")
        return classified
    
    def _analyze_export_issues(self, export_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze export functionality issues."""
        if not export_conversations:
            return {"total_export_issues": 0, "export_types": {}, "common_errors": {}}
        
        export_types = Counter()
        common_errors = Counter()
        export_sizes = []
        export_formats = Counter()
        
        for conv in export_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify export types
            for export_type, keywords in self.export_keywords.items():
                if any(keyword in text for keyword in keywords):
                    export_types[export_type] += 1
                    break
            
            # Identify common export errors
            if 'failed' in text or 'error' in text:
                if 'timeout' in text:
                    common_errors['Export Timeout'] += 1
                elif 'format' in text:
                    common_errors['Format Error'] += 1
                elif 'size' in text or 'large' in text:
                    common_errors['Size Limit Exceeded'] += 1
                elif 'permission' in text or 'access' in text:
                    common_errors['Permission Error'] += 1
                else:
                    common_errors['General Export Error'] += 1
            
            # Extract export sizes
            size_match = re.search(r'(\d+)\s*(mb|gb|kb)', text)
            if size_match:
                size = int(size_match.group(1))
                unit = size_match.group(2).lower()
                if unit == 'gb':
                    size *= 1024  # Convert to MB
                elif unit == 'kb':
                    size /= 1024  # Convert to MB
                export_sizes.append(size)
            
            # Identify export formats
            if 'csv' in text:
                export_formats['CSV'] += 1
            if 'excel' in text or 'xlsx' in text:
                export_formats['Excel'] += 1
            if 'json' in text:
                export_formats['JSON'] += 1
            if 'pdf' in text:
                export_formats['PDF'] += 1
        
        return {
            "total_export_issues": len(export_conversations),
            "export_types": dict(export_types.most_common()),
            "common_errors": dict(common_errors.most_common()),
            "export_formats": dict(export_formats.most_common()),
            "average_export_size_mb": sum(export_sizes) / len(export_sizes) if export_sizes else 0,
            "export_sizes": export_sizes
        }
    
    def _analyze_product_bugs(self, bug_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze product bugs and errors."""
        if not bug_conversations:
            return {"total_bugs": 0, "bug_severity": {}, "bug_categories": {}}
        
        bug_severity = Counter()
        bug_categories = Counter()
        bug_resolution_times = []
        
        for conv in bug_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Determine bug severity
            severity_detected = False
            for severity, keywords in self.bug_severity_keywords.items():
                if any(keyword in text for keyword in keywords):
                    bug_severity[severity] += 1
                    conv['bug_severity'] = severity
                    severity_detected = True
                    break
            
            if not severity_detected:
                bug_severity['unknown'] += 1
                conv['bug_severity'] = 'unknown'
            
            # Categorize bugs
            if 'ui' in text or 'interface' in text or 'display' in text:
                bug_categories['UI/Interface'] += 1
            elif 'performance' in text or 'slow' in text or 'speed' in text:
                bug_categories['Performance'] += 1
            elif 'data' in text or 'information' in text:
                bug_categories['Data Issues'] += 1
            elif 'login' in text or 'authentication' in text:
                bug_categories['Authentication'] += 1
            elif 'export' in text or 'download' in text:
                bug_categories['Export/Download'] += 1
            elif 'api' in text or 'integration' in text:
                bug_categories['API/Integration'] += 1
            else:
                bug_categories['Other'] += 1
            
            # Calculate resolution time
            resolution_time = self._calculate_resolution_time(conv)
            if resolution_time:
                bug_resolution_times.append(resolution_time)
        
        return {
            "total_bugs": len(bug_conversations),
            "bug_severity": dict(bug_severity.most_common()),
            "bug_categories": dict(bug_categories.most_common()),
            "average_resolution_time_hours": sum(bug_resolution_times) / len(bug_resolution_times) if bug_resolution_times else 0,
            "resolution_times": bug_resolution_times
        }
    
    def _analyze_feature_requests(self, feature_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze feature requests and suggestions."""
        if not feature_conversations:
            return {"total_feature_requests": 0, "feature_categories": {}, "priority_features": {}}
        
        feature_categories = Counter()
        priority_features = Counter()
        feature_urgency = Counter()
        
        for conv in feature_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Categorize feature requests
            if 'export' in text or 'download' in text:
                feature_categories['Export/Download'] += 1
            elif 'integration' in text or 'api' in text:
                feature_categories['Integration/API'] += 1
            elif 'ui' in text or 'interface' in text:
                feature_categories['UI/Interface'] += 1
            elif 'report' in text or 'analytics' in text:
                feature_categories['Reporting/Analytics'] += 1
            elif 'automation' in text or 'workflow' in text:
                feature_categories['Automation/Workflow'] += 1
            elif 'mobile' in text or 'app' in text:
                feature_categories['Mobile/App'] += 1
            else:
                feature_categories['Other'] += 1
            
            # Determine feature priority
            if 'urgent' in text or 'critical' in text or 'important' in text:
                priority_features['High Priority'] += 1
                feature_urgency['urgent'] += 1
            elif 'nice to have' in text or 'would be nice' in text:
                priority_features['Low Priority'] += 1
                feature_urgency['nice_to_have'] += 1
            else:
                priority_features['Medium Priority'] += 1
                feature_urgency['medium'] += 1
        
        return {
            "total_feature_requests": len(feature_conversations),
            "feature_categories": dict(feature_categories.most_common()),
            "priority_features": dict(priority_features.most_common()),
            "feature_urgency": dict(feature_urgency.most_common())
        }
    
    def _analyze_usage_questions(self, usage_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze product usage questions and tutorials."""
        if not usage_conversations:
            return {"total_usage_questions": 0, "question_categories": {}, "common_topics": {}}
        
        question_categories = Counter()
        common_topics = Counter()
        question_complexity = Counter()
        
        for conv in usage_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Categorize usage questions
            if 'how to' in text:
                question_categories['How-to Questions'] += 1
            elif 'tutorial' in text or 'guide' in text:
                question_categories['Tutorial Requests'] += 1
            elif 'help' in text:
                question_categories['General Help'] += 1
            elif 'question' in text:
                question_categories['Specific Questions'] += 1
            else:
                question_categories['Other'] += 1
            
            # Identify common topics
            if 'export' in text:
                common_topics['Export'] += 1
            elif 'import' in text:
                common_topics['Import'] += 1
            elif 'settings' in text:
                common_topics['Settings'] += 1
            elif 'permissions' in text:
                common_topics['Permissions'] += 1
            elif 'reports' in text:
                common_topics['Reports'] += 1
            elif 'dashboard' in text:
                common_topics['Dashboard'] += 1
            
            # Determine question complexity
            if len(text.split()) > 100:
                question_complexity['Complex'] += 1
            elif len(text.split()) > 50:
                question_complexity['Medium'] += 1
            else:
                question_complexity['Simple'] += 1
        
        return {
            "total_usage_questions": len(usage_conversations),
            "question_categories": dict(question_categories.most_common()),
            "common_topics": dict(common_topics.most_common()),
            "question_complexity": dict(question_complexity.most_common())
        }
    
    def _analyze_technical_issues(self, technical_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze technical product issues."""
        if not technical_conversations:
            return {"total_technical_issues": 0, "technical_categories": {}, "escalation_patterns": {}}
        
        technical_categories = Counter()
        escalation_patterns = Counter()
        technical_complexity = Counter()
        
        for conv in technical_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Categorize technical issues
            if 'api' in text:
                technical_categories['API Issues'] += 1
            elif 'integration' in text:
                technical_categories['Integration Issues'] += 1
            elif 'authentication' in text or 'login' in text:
                technical_categories['Authentication Issues'] += 1
            elif 'connection' in text or 'network' in text:
                technical_categories['Connection Issues'] += 1
            elif 'performance' in text or 'speed' in text:
                technical_categories['Performance Issues'] += 1
            elif 'data' in text or 'database' in text:
                technical_categories['Data Issues'] += 1
            else:
                technical_categories['Other Technical'] += 1
            
            # Identify escalation patterns
            if 'escalate' in text or 'escalation' in text:
                escalation_patterns['Escalated'] += 1
            elif 'technical' in text and ('complex' in text or 'advanced' in text):
                escalation_patterns['Complex Technical'] += 1
            elif 'engineer' in text or 'developer' in text:
                escalation_patterns['Engineering Required'] += 1
            else:
                escalation_patterns['Standard Technical'] += 1
            
            # Determine technical complexity
            technical_terms = ['api', 'endpoint', 'authentication', 'integration', 'database', 'server']
            term_count = sum(1 for term in technical_terms if term in text)
            
            if term_count >= 3:
                technical_complexity['High'] += 1
            elif term_count >= 1:
                technical_complexity['Medium'] += 1
            else:
                technical_complexity['Low'] += 1
        
        return {
            "total_technical_issues": len(technical_conversations),
            "technical_categories": dict(technical_categories.most_common()),
            "escalation_patterns": dict(escalation_patterns.most_common()),
            "technical_complexity": dict(technical_complexity.most_common())
        }
    
    def _calculate_product_metrics(self, conversations: List[Dict[str, Any]], classified: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Calculate overall product metrics."""
        total_conversations = len(conversations)
        
        # Calculate percentages
        export_percentage = (len(classified['export']) / total_conversations * 100) if total_conversations > 0 else 0
        bug_percentage = (len(classified['bug']) / total_conversations * 100) if total_conversations > 0 else 0
        feature_percentage = (len(classified['feature']) / total_conversations * 100) if total_conversations > 0 else 0
        usage_percentage = (len(classified['usage']) / total_conversations * 100) if total_conversations > 0 else 0
        technical_percentage = (len(classified['technical']) / total_conversations * 100) if total_conversations > 0 else 0
        
        # Calculate resolution rates
        resolved_conversations = sum(1 for conv in conversations if conv.get('state', '').lower() == 'closed')
        resolution_rate = (resolved_conversations / total_conversations) if total_conversations > 0 else 0
        
        return {
            "total_product_conversations": total_conversations,
            "category_distribution": {
                "export_percentage": export_percentage,
                "bug_percentage": bug_percentage,
                "feature_percentage": feature_percentage,
                "usage_percentage": usage_percentage,
                "technical_percentage": technical_percentage
            },
            "overall_resolution_rate": resolution_rate,
            "resolved_conversations": resolved_conversations
        }
    
    def _identify_product_trends(self, conversations: List[Dict[str, Any]], start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Identify product trends over time."""
        # Group conversations by date and product type
        daily_counts = {}
        daily_types = {}
        
        for conv in conversations:
            created_at = conv.get('created_at')
            if created_at:
                # Use helper to handle both datetime and numeric types
                dt = to_utc_datetime(created_at)
                if not dt:
                    continue
                
                date_key = dt.date().isoformat()
                daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
                
                product_type = conv.get('product_type', 'other')
                if date_key not in daily_types:
                    daily_types[date_key] = Counter()
                daily_types[date_key][product_type] += 1
        
        # Calculate trends
        dates = sorted(daily_counts.keys())
        if len(dates) < 2:
            return {"trend": "insufficient_data", "daily_counts": daily_counts}
        
        # Simple trend calculation
        first_half = sum(daily_counts[date] for date in dates[:len(dates)//2])
        second_half = sum(daily_counts[date] for date in dates[len(dates)//2:])
        
        if second_half > first_half * 1.1:
            trend = "increasing"
        elif second_half < first_half * 0.9:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "daily_counts": daily_counts,
            "daily_types": {date: dict(types) for date, types in daily_types.items()},
            "total_days": len(dates),
            "average_daily": sum(daily_counts.values()) / len(daily_counts) if daily_counts else 0
        }
    
    def _identify_common_product_issues(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify common product issues and patterns."""
        issue_patterns = Counter()
        issue_examples = {}
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify common issue patterns
            if 'export' in text and 'failed' in text:
                issue_patterns['Export Failed'] += 1
                if 'Export Failed' not in issue_examples:
                    issue_examples['Export Failed'] = text[:200] + "..."
            
            elif 'bug' in text and 'not working' in text:
                issue_patterns['Product Not Working'] += 1
                if 'Product Not Working' not in issue_examples:
                    issue_examples['Product Not Working'] = text[:200] + "..."
            
            elif 'how to' in text and 'export' in text:
                issue_patterns['How to Export'] += 1
                if 'How to Export' not in issue_examples:
                    issue_examples['How to Export'] = text[:200] + "..."
            
            elif 'feature' in text and 'request' in text:
                issue_patterns['Feature Request'] += 1
                if 'Feature Request' not in issue_examples:
                    issue_examples['Feature Request'] = text[:200] + "..."
            
            elif 'api' in text and 'error' in text:
                issue_patterns['API Error'] += 1
                if 'API Error' not in issue_examples:
                    issue_examples['API Error'] = text[:200] + "..."
        
        # Format common issues
        common_issues = []
        for issue, count in issue_patterns.most_common(10):
            common_issues.append({
                "issue": issue,
                "count": count,
                "example": issue_examples.get(issue, "No example available")
            })
        
        return common_issues
    
    def _analyze_product_satisfaction(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze customer satisfaction with product interactions."""
        satisfaction_ratings = []
        satisfaction_keywords = {
            'positive': ['satisfied', 'happy', 'great', 'excellent', 'thank you', 'resolved', 'working'],
            'negative': ['frustrated', 'angry', 'disappointed', 'unhappy', 'terrible', 'awful', 'broken'],
            'neutral': ['okay', 'fine', 'acceptable', 'average', 'working']
        }
        
        sentiment_counts = Counter()
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Check for explicit satisfaction ratings
            custom_attrs = conv.get('custom_attributes', {})
            rating = custom_attrs.get('satisfaction_rating') or custom_attrs.get('rating')
            if rating:
                try:
                    satisfaction_ratings.append(float(rating))
                except (ValueError, TypeError):
                    pass
            
            # Analyze sentiment from text
            positive_count = sum(1 for keyword in satisfaction_keywords['positive'] if keyword in text)
            negative_count = sum(1 for keyword in satisfaction_keywords['negative'] if keyword in text)
            neutral_count = sum(1 for keyword in satisfaction_keywords['neutral'] if keyword in text)
            
            if positive_count > negative_count and positive_count > neutral_count:
                sentiment_counts['positive'] += 1
            elif negative_count > positive_count and negative_count > neutral_count:
                sentiment_counts['negative'] += 1
            else:
                sentiment_counts['neutral'] += 1
        
        return {
            "explicit_ratings": {
                "count": len(satisfaction_ratings),
                "average": sum(satisfaction_ratings) / len(satisfaction_ratings) if satisfaction_ratings else 0
            },
            "sentiment_analysis": dict(sentiment_counts.most_common()),
            "total_analyzed": len(conversations)
        }
    
    def _identify_macro_opportunities(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify macro opportunities from product conversations."""
        macro_patterns = Counter()
        macro_examples = {}
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Look for common response patterns that could be macros
            if 'export' in text and ('how to' in text or 'step' in text):
                macro_patterns['Export Instructions'] += 1
                if 'Export Instructions' not in macro_examples:
                    macro_examples['Export Instructions'] = text[:300] + "..."
            
            elif 'bug' in text and ('report' in text or 'submit' in text):
                macro_patterns['Bug Report Instructions'] += 1
                if 'Bug Report Instructions' not in macro_examples:
                    macro_examples['Bug Report Instructions'] = text[:300] + "..."
            
            elif 'feature' in text and ('request' in text or 'suggestion' in text):
                macro_patterns['Feature Request Process'] += 1
                if 'Feature Request Process' not in macro_examples:
                    macro_examples['Feature Request Process'] = text[:300] + "..."
            
            elif 'tutorial' in text or 'guide' in text:
                macro_patterns['Tutorial Links'] += 1
                if 'Tutorial Links' not in macro_examples:
                    macro_examples['Tutorial Links'] = text[:300] + "..."
        
        # Format macro opportunities
        macro_opportunities = []
        for macro, count in macro_patterns.most_common(10):
            if count >= 3:  # Only include macros with 3+ occurrences
                macro_opportunities.append({
                    "macro_name": macro,
                    "occurrences": count,
                    "example": macro_examples.get(macro, "No example available"),
                    "priority": "high" if count >= 10 else "medium" if count >= 5 else "low"
                })
        
        return macro_opportunities
    
    def _calculate_resolution_time(self, conv: Dict[str, Any]) -> Optional[float]:
        """Calculate resolution time in hours."""
        created_at = conv.get('created_at')
        closed_at = conv.get('closed_at')
        
        if created_at and closed_at:
            try:
                # Use helper to calculate time delta in seconds
                delta_seconds = calculate_time_delta_seconds(created_at, closed_at)
                if delta_seconds is not None:
                    return delta_seconds / 3600  # Convert to hours
            except Exception as e:
                self.logger.warning(f"Error calculating resolution time: {e}")
                return None
        
        return None
    
    def _get_ai_analysis_prompt(self, data_summary: str) -> str:
        """Get AI analysis prompt for product analysis."""
        return PromptTemplates.get_custom_analysis_prompt(
            custom_prompt="Analyze product conversations focusing on export issues, product bugs, feature requests, usage questions, and technical problems",
            start_date="",
            end_date="",
            intercom_data=data_summary
        )
