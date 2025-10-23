"""
API Analyzer for Intercom Analysis Tool.
Specialized analyzer for API-related conversations including technical issues, integrations, and authentication problems.
"""

import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from collections import Counter

from src.analyzers.base_category_analyzer import BaseCategoryAnalyzer, AnalysisError
from src.config.prompts import PromptTemplates

logger = logging.getLogger(__name__)


class ApiAnalyzer(BaseCategoryAnalyzer):
    """
    Specialized analyzer for API-related conversations.
    
    Focuses on:
    - API authentication and authorization
    - API integration issues
    - API performance and rate limiting
    - API documentation and usage
    - Technical troubleshooting
    """
    
    def __init__(self, **kwargs):
        """Initialize API analyzer."""
        super().__init__(category_name="API", **kwargs)
        
        # API-specific patterns
        self.authentication_patterns = [
            r'authentication', r'auth', r'login', r'token', r'api.*key',
            r'credentials', r'authorization', r'bearer', r'oauth'
        ]
        
        self.integration_patterns = [
            r'integration', r'webhook', r'endpoint', r'api.*call',
            r'request', r'response', r'http', r'rest', r'graphql'
        ]
        
        self.performance_patterns = [
            r'performance', r'speed', r'slow', r'timeout', r'rate.*limit',
            r'throttling', r'latency', r'response.*time'
        ]
        
        self.error_patterns = [
            r'error', r'bug', r'failed', r'not working', r'issue',
            r'exception', r'crash', r'broken', r'problem'
        ]
        
        # API keywords for classification
        self.api_keywords = {
            'authentication': ['authentication', 'auth', 'login', 'token', 'api key', 'credentials', 'authorization'],
            'integration': ['integration', 'webhook', 'endpoint', 'api call', 'request', 'response', 'http'],
            'performance': ['performance', 'speed', 'slow', 'timeout', 'rate limit', 'throttling', 'latency'],
            'documentation': ['documentation', 'docs', 'guide', 'tutorial', 'example', 'help', 'how to'],
            'error': ['error', 'bug', 'failed', 'not working', 'issue', 'exception', 'crash']
        }
        
        # Authentication-specific keywords
        self.authentication_keywords = {
            'api_key_issues': ['api key', 'key', 'token', 'authentication failed', 'invalid key'],
            'oauth_issues': ['oauth', 'bearer', 'authorization', 'scope', 'permission'],
            'login_issues': ['login', 'sign in', 'credentials', 'password', 'username'],
            'token_issues': ['token', 'expired', 'refresh', 'jwt', 'access token']
        }
        
        # Integration-specific keywords
        self.integration_keywords = {
            'webhook_issues': ['webhook', 'callback', 'notification', 'event'],
            'endpoint_issues': ['endpoint', 'url', 'path', 'route', 'api call'],
            'request_issues': ['request', 'post', 'get', 'put', 'delete', 'http method'],
            'response_issues': ['response', 'status code', 'error code', 'http status']
        }
        
        # Error severity indicators
        self.error_severity_keywords = {
            'critical': ['critical', 'urgent', 'blocking', 'cannot work', 'completely broken', 'down'],
            'high': ['major', 'important', 'significant', 'serious', 'failing'],
            'medium': ['moderate', 'minor', 'inconvenience', 'intermittent'],
            'low': ['cosmetic', 'minor', 'small', 'trivial', 'warning']
        }
        
        # HTTP status code patterns
        self.http_status_patterns = {
            '4xx': [r'40[0-9]', r'4\d{2}'],
            '5xx': [r'50[0-9]', r'5\d{2}'],
            '2xx': [r'20[0-9]', r'2\d{2}']
        }
        
        self.logger.info("Initialized ApiAnalyzer with specialized API patterns")
    
    async def _perform_category_analysis(
        self, 
        conversations: List[Dict[str, Any]], 
        start_date: datetime, 
        end_date: datetime,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform API-specific analysis.
        
        Args:
            conversations: Filtered API conversations
            start_date: Analysis start date
            end_date: Analysis end date
            options: Analysis options
            
        Returns:
            API-specific analysis results
        """
        self.logger.info(f"Performing API analysis on {len(conversations)} conversations")
        
        try:
            # Classify conversations by API type
            classified_conversations = self._classify_api_conversations(conversations)
            
            # Analyze authentication issues
            authentication_analysis = self._analyze_authentication_issues(classified_conversations['authentication'])
            
            # Analyze integration issues
            integration_analysis = self._analyze_integration_issues(classified_conversations['integration'])
            
            # Analyze performance issues
            performance_analysis = self._analyze_performance_issues(classified_conversations['performance'])
            
            # Analyze documentation issues
            documentation_analysis = self._analyze_documentation_issues(classified_conversations['documentation'])
            
            # Analyze error patterns
            error_analysis = self._analyze_error_patterns(classified_conversations['error'])
            
            # Calculate API metrics
            api_metrics = self._calculate_api_metrics(conversations, classified_conversations)
            
            # Identify API trends
            api_trends = self._identify_api_trends(conversations, start_date, end_date)
            
            # Find common API issues
            common_issues = self._identify_common_api_issues(conversations)
            
            # Analyze API satisfaction
            api_satisfaction = self._analyze_api_satisfaction(conversations)
            
            # Identify macro opportunities
            macro_opportunities = self._identify_macro_opportunities(conversations)
            
            # Analyze technical complexity
            technical_complexity = self._analyze_technical_complexity(conversations)
            
            return {
                "analysis_type": "api_analysis",
                "conversation_count": len(conversations),
                "classified_conversations": {
                    category: len(convs) for category, convs in classified_conversations.items()
                },
                "authentication_analysis": authentication_analysis,
                "integration_analysis": integration_analysis,
                "performance_analysis": performance_analysis,
                "documentation_analysis": documentation_analysis,
                "error_analysis": error_analysis,
                "api_metrics": api_metrics,
                "api_trends": api_trends,
                "common_issues": common_issues,
                "api_satisfaction": api_satisfaction,
                "macro_opportunities": macro_opportunities,
                "technical_complexity": technical_complexity
            }
            
        except Exception as e:
            self.logger.error(f"API analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"Failed to perform API analysis: {e}") from e
    
    def _classify_api_conversations(self, conversations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Classify conversations by API type."""
        classified = {
            'authentication': [],
            'integration': [],
            'performance': [],
            'documentation': [],
            'error': [],
            'other': []
        }
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            classified_into = False
            
            # Check each API type
            for api_type, keywords in self.api_keywords.items():
                if any(keyword in text for keyword in keywords):
                    classified[api_type].append(conv)
                    conv['api_type'] = api_type
                    classified_into = True
                    break
            
            if not classified_into:
                classified['other'].append(conv)
                conv['api_type'] = 'other'
        
        self.logger.info(f"Classified conversations: {[(k, len(v)) for k, v in classified.items()]}")
        return classified
    
    def _analyze_authentication_issues(self, authentication_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze API authentication issues."""
        if not authentication_conversations:
            return {"total_authentication_issues": 0, "auth_issue_types": {}, "token_issues": {}}
        
        auth_issue_types = Counter()
        token_issues = Counter()
        oauth_issues = Counter()
        api_key_issues = Counter()
        
        for conv in authentication_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify authentication issue types
            for issue_type, keywords in self.authentication_keywords.items():
                if any(keyword in text for keyword in keywords):
                    if issue_type == 'api_key_issues':
                        api_key_issues['API Key Issues'] += 1
                    elif issue_type == 'oauth_issues':
                        oauth_issues['OAuth Issues'] += 1
                    elif issue_type == 'login_issues':
                        auth_issue_types['Login Issues'] += 1
                    elif issue_type == 'token_issues':
                        token_issues['Token Issues'] += 1
            
            # General authentication issue classification
            if 'api key' in text or 'key' in text:
                auth_issue_types['API Key Issues'] += 1
            elif 'oauth' in text or 'bearer' in text:
                auth_issue_types['OAuth Issues'] += 1
            elif 'token' in text:
                auth_issue_types['Token Issues'] += 1
            elif 'login' in text or 'sign in' in text:
                auth_issue_types['Login Issues'] += 1
            elif 'permission' in text or 'access' in text:
                auth_issue_types['Permission Issues'] += 1
            else:
                auth_issue_types['Other Authentication Issues'] += 1
        
        return {
            "total_authentication_issues": len(authentication_conversations),
            "auth_issue_types": dict(auth_issue_types.most_common()),
            "token_issues": dict(token_issues.most_common()),
            "oauth_issues": dict(oauth_issues.most_common()),
            "api_key_issues": dict(api_key_issues.most_common())
        }
    
    def _analyze_integration_issues(self, integration_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze API integration issues."""
        if not integration_conversations:
            return {"total_integration_issues": 0, "integration_issue_types": {}, "webhook_issues": {}}
        
        integration_issue_types = Counter()
        webhook_issues = Counter()
        endpoint_issues = Counter()
        request_response_issues = Counter()
        
        for conv in integration_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify integration issue types
            for issue_type, keywords in self.integration_keywords.items():
                if any(keyword in text for keyword in keywords):
                    if issue_type == 'webhook_issues':
                        webhook_issues['Webhook Issues'] += 1
                    elif issue_type == 'endpoint_issues':
                        endpoint_issues['Endpoint Issues'] += 1
                    elif issue_type == 'request_issues':
                        request_response_issues['Request Issues'] += 1
                    elif issue_type == 'response_issues':
                        request_response_issues['Response Issues'] += 1
            
            # General integration issue classification
            if 'webhook' in text:
                integration_issue_types['Webhook Issues'] += 1
            elif 'endpoint' in text or 'url' in text:
                integration_issue_types['Endpoint Issues'] += 1
            elif 'request' in text or 'post' in text or 'get' in text:
                integration_issue_types['Request Issues'] += 1
            elif 'response' in text or 'status' in text:
                integration_issue_types['Response Issues'] += 1
            elif 'integration' in text:
                integration_issue_types['General Integration Issues'] += 1
            else:
                integration_issue_types['Other Integration Issues'] += 1
        
        return {
            "total_integration_issues": len(integration_conversations),
            "integration_issue_types": dict(integration_issue_types.most_common()),
            "webhook_issues": dict(webhook_issues.most_common()),
            "endpoint_issues": dict(endpoint_issues.most_common()),
            "request_response_issues": dict(request_response_issues.most_common())
        }
    
    def _analyze_performance_issues(self, performance_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze API performance issues."""
        if not performance_conversations:
            return {"total_performance_issues": 0, "performance_issue_types": {}, "rate_limiting": {}}
        
        performance_issue_types = Counter()
        rate_limiting_issues = Counter()
        timeout_issues = Counter()
        latency_issues = Counter()
        
        for conv in performance_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify performance issue types
            if 'rate limit' in text or 'throttling' in text:
                performance_issue_types['Rate Limiting'] += 1
                rate_limiting_issues['Rate Limiting'] += 1
            elif 'timeout' in text:
                performance_issue_types['Timeout Issues'] += 1
                timeout_issues['Timeout Issues'] += 1
            elif 'slow' in text or 'latency' in text:
                performance_issue_types['Latency Issues'] += 1
                latency_issues['Latency Issues'] += 1
            elif 'performance' in text:
                performance_issue_types['General Performance Issues'] += 1
            else:
                performance_issue_types['Other Performance Issues'] += 1
        
        return {
            "total_performance_issues": len(performance_conversations),
            "performance_issue_types": dict(performance_issue_types.most_common()),
            "rate_limiting": dict(rate_limiting_issues.most_common()),
            "timeout_issues": dict(timeout_issues.most_common()),
            "latency_issues": dict(latency_issues.most_common())
        }
    
    def _analyze_documentation_issues(self, documentation_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze API documentation issues."""
        if not documentation_conversations:
            return {"total_documentation_issues": 0, "doc_issue_types": {}, "help_requests": {}}
        
        doc_issue_types = Counter()
        help_requests = Counter()
        tutorial_requests = Counter()
        example_requests = Counter()
        
        for conv in documentation_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify documentation issue types
            if 'how to' in text or 'tutorial' in text:
                doc_issue_types['How-to Questions'] += 1
                tutorial_requests['Tutorial Requests'] += 1
            elif 'example' in text or 'sample' in text:
                doc_issue_types['Example Requests'] += 1
                example_requests['Example Requests'] += 1
            elif 'help' in text or 'guide' in text:
                doc_issue_types['Help Requests'] += 1
                help_requests['Help Requests'] += 1
            elif 'documentation' in text or 'docs' in text:
                doc_issue_types['Documentation Issues'] += 1
            else:
                doc_issue_types['Other Documentation Issues'] += 1
        
        return {
            "total_documentation_issues": len(documentation_conversations),
            "doc_issue_types": dict(doc_issue_types.most_common()),
            "help_requests": dict(help_requests.most_common()),
            "tutorial_requests": dict(tutorial_requests.most_common()),
            "example_requests": dict(example_requests.most_common())
        }
    
    def _analyze_error_patterns(self, error_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze API error patterns."""
        if not error_conversations:
            return {"total_errors": 0, "error_severity": {}, "error_categories": {}}
        
        error_severity = Counter()
        error_categories = Counter()
        http_status_codes = Counter()
        error_resolution_times = []
        
        for conv in error_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Determine error severity
            severity_detected = False
            for severity, keywords in self.error_severity_keywords.items():
                if any(keyword in text for keyword in keywords):
                    error_severity[severity] += 1
                    conv['error_severity'] = severity
                    severity_detected = True
                    break
            
            if not severity_detected:
                error_severity['unknown'] += 1
                conv['error_severity'] = 'unknown'
            
            # Categorize errors
            if 'authentication' in text or 'auth' in text:
                error_categories['Authentication Errors'] += 1
            elif 'permission' in text or 'access' in text:
                error_categories['Permission Errors'] += 1
            elif 'validation' in text or 'invalid' in text:
                error_categories['Validation Errors'] += 1
            elif 'server' in text or 'internal' in text:
                error_categories['Server Errors'] += 1
            elif 'timeout' in text:
                error_categories['Timeout Errors'] += 1
            else:
                error_categories['Other Errors'] += 1
            
            # Extract HTTP status codes
            for status_range, patterns in self.http_status_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text):
                        http_status_codes[status_range] += 1
                        break
            
            # Calculate resolution time
            resolution_time = self._calculate_resolution_time(conv)
            if resolution_time:
                error_resolution_times.append(resolution_time)
        
        return {
            "total_errors": len(error_conversations),
            "error_severity": dict(error_severity.most_common()),
            "error_categories": dict(error_categories.most_common()),
            "http_status_codes": dict(http_status_codes.most_common()),
            "average_resolution_time_hours": sum(error_resolution_times) / len(error_resolution_times) if error_resolution_times else 0,
            "resolution_times": error_resolution_times
        }
    
    def _calculate_api_metrics(self, conversations: List[Dict[str, Any]], classified: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Calculate overall API metrics."""
        total_conversations = len(conversations)
        
        # Calculate percentages
        auth_percentage = (len(classified['authentication']) / total_conversations * 100) if total_conversations > 0 else 0
        integration_percentage = (len(classified['integration']) / total_conversations * 100) if total_conversations > 0 else 0
        performance_percentage = (len(classified['performance']) / total_conversations * 100) if total_conversations > 0 else 0
        documentation_percentage = (len(classified['documentation']) / total_conversations * 100) if total_conversations > 0 else 0
        error_percentage = (len(classified['error']) / total_conversations * 100) if total_conversations > 0 else 0
        
        # Calculate resolution rates
        resolved_conversations = sum(1 for conv in conversations if conv.get('state', '').lower() == 'closed')
        resolution_rate = (resolved_conversations / total_conversations) if total_conversations > 0 else 0
        
        return {
            "total_api_conversations": total_conversations,
            "category_distribution": {
                "authentication_percentage": auth_percentage,
                "integration_percentage": integration_percentage,
                "performance_percentage": performance_percentage,
                "documentation_percentage": documentation_percentage,
                "error_percentage": error_percentage
            },
            "overall_resolution_rate": resolution_rate,
            "resolved_conversations": resolved_conversations
        }
    
    def _identify_api_trends(self, conversations: List[Dict[str, Any]], start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Identify API trends over time."""
        # Group conversations by date and API type
        daily_counts = {}
        daily_types = {}
        
        for conv in conversations:
            created_at = conv.get('created_at')
            if created_at:
                if isinstance(created_at, (int, float)):
                    created_at = datetime.fromtimestamp(created_at)
                
                date_key = created_at.date().isoformat()
                daily_counts[date_key] = daily_counts.get(date_key, 0) + 1
                
                api_type = conv.get('api_type', 'other')
                if date_key not in daily_types:
                    daily_types[date_key] = Counter()
                daily_types[date_key][api_type] += 1
        
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
    
    def _identify_common_api_issues(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify common API issues and patterns."""
        issue_patterns = Counter()
        issue_examples = {}
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify common issue patterns
            if 'api key' in text and 'invalid' in text:
                issue_patterns['Invalid API Key'] += 1
                if 'Invalid API Key' not in issue_examples:
                    issue_examples['Invalid API Key'] = text[:200] + "..."
            
            elif 'authentication' in text and 'failed' in text:
                issue_patterns['Authentication Failed'] += 1
                if 'Authentication Failed' not in issue_examples:
                    issue_examples['Authentication Failed'] = text[:200] + "..."
            
            elif 'rate limit' in text:
                issue_patterns['Rate Limit Exceeded'] += 1
                if 'Rate Limit Exceeded' not in issue_examples:
                    issue_examples['Rate Limit Exceeded'] = text[:200] + "..."
            
            elif 'webhook' in text and 'not working' in text:
                issue_patterns['Webhook Not Working'] += 1
                if 'Webhook Not Working' not in issue_examples:
                    issue_examples['Webhook Not Working'] = text[:200] + "..."
            
            elif 'endpoint' in text and 'error' in text:
                issue_patterns['Endpoint Error'] += 1
                if 'Endpoint Error' not in issue_examples:
                    issue_examples['Endpoint Error'] = text[:200] + "..."
        
        # Format common issues
        common_issues = []
        for issue, count in issue_patterns.most_common(10):
            common_issues.append({
                "issue": issue,
                "count": count,
                "example": issue_examples.get(issue, "No example available")
            })
        
        return common_issues
    
    def _analyze_api_satisfaction(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze customer satisfaction with API interactions."""
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
        """Identify macro opportunities from API conversations."""
        macro_patterns = Counter()
        macro_examples = {}
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Look for common response patterns that could be macros
            if 'api key' in text and ('how to' in text or 'setup' in text):
                macro_patterns['API Key Setup Instructions'] += 1
                if 'API Key Setup Instructions' not in macro_examples:
                    macro_examples['API Key Setup Instructions'] = text[:300] + "..."
            
            elif 'authentication' in text and ('error' in text or 'failed' in text):
                macro_patterns['Authentication Troubleshooting'] += 1
                if 'Authentication Troubleshooting' not in macro_examples:
                    macro_examples['Authentication Troubleshooting'] = text[:300] + "..."
            
            elif 'webhook' in text and ('setup' in text or 'configuration' in text):
                macro_patterns['Webhook Setup Guide'] += 1
                if 'Webhook Setup Guide' not in macro_examples:
                    macro_examples['Webhook Setup Guide'] = text[:300] + "..."
            
            elif 'rate limit' in text and ('exceeded' in text or 'throttling' in text):
                macro_patterns['Rate Limit Handling'] += 1
                if 'Rate Limit Handling' not in macro_examples:
                    macro_examples['Rate Limit Handling'] = text[:300] + "..."
        
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
    
    def _analyze_technical_complexity(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze technical complexity of API conversations."""
        complexity_levels = Counter()
        technical_terms = Counter()
        
        # Technical terms that indicate complexity
        high_complexity_terms = ['oauth', 'jwt', 'webhook', 'endpoint', 'authentication', 'authorization']
        medium_complexity_terms = ['api', 'token', 'request', 'response', 'http', 'integration']
        low_complexity_terms = ['key', 'login', 'password', 'help', 'documentation']
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Count technical terms
            high_count = sum(1 for term in high_complexity_terms if term in text)
            medium_count = sum(1 for term in medium_complexity_terms if term in text)
            low_count = sum(1 for term in low_complexity_terms if term in text)
            
            # Determine complexity level
            if high_count >= 2:
                complexity_levels['High'] += 1
            elif high_count >= 1 or medium_count >= 3:
                complexity_levels['Medium'] += 1
            elif low_count >= 1 or medium_count >= 1:
                complexity_levels['Low'] += 1
            else:
                complexity_levels['Unknown'] += 1
            
            # Count individual technical terms
            for term in high_complexity_terms + medium_complexity_terms + low_complexity_terms:
                if term in text:
                    technical_terms[term] += 1
        
        return {
            "complexity_distribution": dict(complexity_levels.most_common()),
            "most_common_technical_terms": dict(technical_terms.most_common(10)),
            "total_conversations_analyzed": len(conversations)
        }
    
    def _calculate_resolution_time(self, conv: Dict[str, Any]) -> Optional[float]:
        """Calculate resolution time in hours."""
        created_at = conv.get('created_at')
        closed_at = conv.get('closed_at')
        
        if created_at and closed_at:
            try:
                if isinstance(created_at, (int, float)):
                    created_at = datetime.fromtimestamp(created_at)
                if isinstance(closed_at, (int, float)):
                    closed_at = datetime.fromtimestamp(closed_at)
                
                resolution_time = (closed_at - created_at).total_seconds() / 3600  # hours
                return resolution_time
            except Exception as e:
                self.logger.warning(f"Error calculating resolution time: {e}")
                return None
        
        return None
    
    def _get_ai_analysis_prompt(self, data_summary: str) -> str:
        """Get AI analysis prompt for API analysis."""
        return PromptTemplates.get_custom_analysis_prompt(
            custom_prompt="Analyze API conversations focusing on authentication issues, integration problems, performance concerns, documentation needs, and technical errors",
            start_date="",
            end_date="",
            intercom_data=data_summary
        )
