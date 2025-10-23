"""
Sites Analyzer for Intercom Analysis Tool.
Specialized analyzer for site-related conversations including domain issues, publishing problems, and education topics.
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


class SitesAnalyzer(BaseCategoryAnalyzer):
    """
    Specialized analyzer for site-related conversations.
    
    Focuses on:
    - Domain and DNS issues
    - Publishing and content management
    - Education and training topics
    - Site performance and accessibility
    - Site configuration and settings
    """
    
    def __init__(self, **kwargs):
        """Initialize sites analyzer."""
        super().__init__(category_name="Workspace", **kwargs)
        
        # Sites-specific patterns
        self.domain_patterns = [
            r'domain', r'dns', r'subdomain', r'url', r'website', r'site',
            r'domain.*name', r'custom.*domain', r'domain.*setup'
        ]
        
        self.publishing_patterns = [
            r'publish', r'publishing', r'content', r'page', r'post', r'article',
            r'blog', r'news', r'update.*content', r'edit.*content'
        ]
        
        self.education_patterns = [
            r'education', r'learning', r'training', r'tutorial', r'course',
            r'lesson', r'student', r'teacher', r'classroom', r'academic'
        ]
        
        self.performance_patterns = [
            r'performance', r'speed', r'slow', r'fast', r'loading', r'load.*time',
            r'optimization', r'cache', r'cdn', r'bandwidth'
        ]
        
        # Sites keywords for classification
        self.sites_keywords = {
            'domain': ['domain', 'dns', 'subdomain', 'url', 'website', 'site', 'domain name'],
            'publishing': ['publish', 'publishing', 'content', 'page', 'post', 'article', 'blog'],
            'education': ['education', 'learning', 'training', 'tutorial', 'course', 'student', 'teacher'],
            'performance': ['performance', 'speed', 'slow', 'fast', 'loading', 'optimization'],
            'configuration': ['settings', 'configuration', 'setup', 'install', 'deploy', 'hosting']
        }
        
        # Domain-specific keywords
        self.domain_keywords = {
            'dns_issues': ['dns', 'nameserver', 'a record', 'cname', 'mx record'],
            'domain_setup': ['domain setup', 'connect domain', 'custom domain', 'domain configuration'],
            'ssl_issues': ['ssl', 'https', 'certificate', 'secure', 'encryption'],
            'subdomain_issues': ['subdomain', 'www', 'app', 'admin', 'api subdomain']
        }
        
        # Publishing-specific keywords
        self.publishing_keywords = {
            'content_management': ['content', 'page', 'post', 'article', 'blog', 'news'],
            'publishing_issues': ['publish', 'publishing', 'not published', 'draft', 'scheduled'],
            'content_editing': ['edit', 'editing', 'update', 'modify', 'change content'],
            'media_issues': ['image', 'video', 'media', 'upload', 'file', 'attachment']
        }
        
        # Education-specific keywords
        self.education_keywords = {
            'course_management': ['course', 'lesson', 'module', 'curriculum', 'syllabus'],
            'student_issues': ['student', 'learner', 'enrollment', 'registration', 'access'],
            'teacher_issues': ['teacher', 'instructor', 'educator', 'admin', 'moderator'],
            'learning_platform': ['learning', 'education', 'training', 'tutorial', 'guide']
        }
        
        self.logger.info("Initialized SitesAnalyzer with specialized sites patterns")
    
    async def _perform_category_analysis(
        self, 
        conversations: List[Dict[str, Any]], 
        start_date: datetime, 
        end_date: datetime,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform sites-specific analysis.
        
        Args:
            conversations: Filtered sites conversations
            start_date: Analysis start date
            end_date: Analysis end date
            options: Analysis options
            
        Returns:
            Sites-specific analysis results
        """
        self.logger.info(f"Performing sites analysis on {len(conversations)} conversations")
        
        try:
            # Classify conversations by sites type
            classified_conversations = self._classify_sites_conversations(conversations)
            
            # Analyze domain issues
            domain_analysis = self._analyze_domain_issues(classified_conversations['domain'])
            
            # Analyze publishing issues
            publishing_analysis = self._analyze_publishing_issues(classified_conversations['publishing'])
            
            # Analyze education topics
            education_analysis = self._analyze_education_topics(classified_conversations['education'])
            
            # Analyze performance issues
            performance_analysis = self._analyze_performance_issues(classified_conversations['performance'])
            
            # Analyze configuration issues
            configuration_analysis = self._analyze_configuration_issues(classified_conversations['configuration'])
            
            # Calculate sites metrics
            sites_metrics = self._calculate_sites_metrics(conversations, classified_conversations)
            
            # Identify sites trends
            sites_trends = self._identify_sites_trends(conversations, start_date, end_date)
            
            # Find common sites issues
            common_issues = self._identify_common_sites_issues(conversations)
            
            # Analyze sites satisfaction
            sites_satisfaction = self._analyze_sites_satisfaction(conversations)
            
            # Identify macro opportunities
            macro_opportunities = self._identify_macro_opportunities(conversations)
            
            return {
                "analysis_type": "sites_analysis",
                "conversation_count": len(conversations),
                "classified_conversations": {
                    category: len(convs) for category, convs in classified_conversations.items()
                },
                "domain_analysis": domain_analysis,
                "publishing_analysis": publishing_analysis,
                "education_analysis": education_analysis,
                "performance_analysis": performance_analysis,
                "configuration_analysis": configuration_analysis,
                "sites_metrics": sites_metrics,
                "sites_trends": sites_trends,
                "common_issues": common_issues,
                "sites_satisfaction": sites_satisfaction,
                "macro_opportunities": macro_opportunities
            }
            
        except Exception as e:
            self.logger.error(f"Sites analysis failed: {e}", exc_info=True)
            raise AnalysisError(f"Failed to perform sites analysis: {e}") from e
    
    def _classify_sites_conversations(self, conversations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Classify conversations by sites type."""
        classified = {
            'domain': [],
            'publishing': [],
            'education': [],
            'performance': [],
            'configuration': [],
            'other': []
        }
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            classified_into = False
            
            # Check each sites type
            for sites_type, keywords in self.sites_keywords.items():
                if any(keyword in text for keyword in keywords):
                    classified[sites_type].append(conv)
                    conv['sites_type'] = sites_type
                    classified_into = True
                    break
            
            if not classified_into:
                classified['other'].append(conv)
                conv['sites_type'] = 'other'
        
        self.logger.info(f"Classified conversations: {[(k, len(v)) for k, v in classified.items()]}")
        return classified
    
    def _analyze_domain_issues(self, domain_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze domain and DNS issues."""
        if not domain_conversations:
            return {"total_domain_issues": 0, "domain_issue_types": {}, "dns_issues": {}}
        
        domain_issue_types = Counter()
        dns_issues = Counter()
        ssl_issues = Counter()
        domain_setup_issues = Counter()
        
        for conv in domain_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify domain issue types
            for issue_type, keywords in self.domain_keywords.items():
                if any(keyword in text for keyword in keywords):
                    if issue_type == 'dns_issues':
                        dns_issues['DNS Issues'] += 1
                    elif issue_type == 'ssl_issues':
                        ssl_issues['SSL Issues'] += 1
                    elif issue_type == 'domain_setup':
                        domain_setup_issues['Domain Setup'] += 1
                    elif issue_type == 'subdomain_issues':
                        domain_setup_issues['Subdomain Issues'] += 1
            
            # General domain issue classification
            if 'not working' in text or 'broken' in text:
                domain_issue_types['Domain Not Working'] += 1
            elif 'setup' in text or 'configuration' in text:
                domain_issue_types['Domain Setup'] += 1
            elif 'ssl' in text or 'https' in text:
                domain_issue_types['SSL/HTTPS Issues'] += 1
            elif 'dns' in text:
                domain_issue_types['DNS Issues'] += 1
            elif 'subdomain' in text:
                domain_issue_types['Subdomain Issues'] += 1
            else:
                domain_issue_types['Other Domain Issues'] += 1
        
        return {
            "total_domain_issues": len(domain_conversations),
            "domain_issue_types": dict(domain_issue_types.most_common()),
            "dns_issues": dict(dns_issues.most_common()),
            "ssl_issues": dict(ssl_issues.most_common()),
            "domain_setup_issues": dict(domain_setup_issues.most_common())
        }
    
    def _analyze_publishing_issues(self, publishing_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze publishing and content management issues."""
        if not publishing_conversations:
            return {"total_publishing_issues": 0, "publishing_issue_types": {}, "content_types": {}}
        
        publishing_issue_types = Counter()
        content_types = Counter()
        media_issues = Counter()
        publishing_workflow = Counter()
        
        for conv in publishing_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify publishing issue types
            for issue_type, keywords in self.publishing_keywords.items():
                if any(keyword in text for keyword in keywords):
                    if issue_type == 'content_management':
                        content_types['Content Management'] += 1
                    elif issue_type == 'publishing_issues':
                        publishing_issue_types['Publishing Issues'] += 1
                    elif issue_type == 'content_editing':
                        publishing_issue_types['Content Editing'] += 1
                    elif issue_type == 'media_issues':
                        media_issues['Media Issues'] += 1
            
            # General publishing issue classification
            if 'not published' in text or 'publish failed' in text:
                publishing_issue_types['Publishing Failed'] += 1
            elif 'edit' in text or 'editing' in text:
                publishing_issue_types['Content Editing'] += 1
            elif 'image' in text or 'video' in text or 'media' in text:
                publishing_issue_types['Media Issues'] += 1
            elif 'draft' in text or 'scheduled' in text:
                publishing_workflow['Publishing Workflow'] += 1
            else:
                publishing_issue_types['Other Publishing Issues'] += 1
            
            # Identify content types
            if 'blog' in text:
                content_types['Blog'] += 1
            elif 'page' in text:
                content_types['Page'] += 1
            elif 'article' in text:
                content_types['Article'] += 1
            elif 'news' in text:
                content_types['News'] += 1
        
        return {
            "total_publishing_issues": len(publishing_conversations),
            "publishing_issue_types": dict(publishing_issue_types.most_common()),
            "content_types": dict(content_types.most_common()),
            "media_issues": dict(media_issues.most_common()),
            "publishing_workflow": dict(publishing_workflow.most_common())
        }
    
    def _analyze_education_topics(self, education_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze education and training topics."""
        if not education_conversations:
            return {"total_education_issues": 0, "education_issue_types": {}, "user_types": {}}
        
        education_issue_types = Counter()
        user_types = Counter()
        course_issues = Counter()
        learning_platform_issues = Counter()
        
        for conv in education_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify education issue types
            for issue_type, keywords in self.education_keywords.items():
                if any(keyword in text for keyword in keywords):
                    if issue_type == 'course_management':
                        course_issues['Course Management'] += 1
                    elif issue_type == 'student_issues':
                        user_types['Student Issues'] += 1
                    elif issue_type == 'teacher_issues':
                        user_types['Teacher Issues'] += 1
                    elif issue_type == 'learning_platform':
                        learning_platform_issues['Learning Platform'] += 1
            
            # General education issue classification
            if 'enrollment' in text or 'registration' in text:
                education_issue_types['Enrollment Issues'] += 1
            elif 'access' in text or 'login' in text:
                education_issue_types['Access Issues'] += 1
            elif 'course' in text:
                education_issue_types['Course Issues'] += 1
            elif 'student' in text:
                education_issue_types['Student Issues'] += 1
            elif 'teacher' in text or 'instructor' in text:
                education_issue_types['Teacher Issues'] += 1
            else:
                education_issue_types['Other Education Issues'] += 1
        
        return {
            "total_education_issues": len(education_conversations),
            "education_issue_types": dict(education_issue_types.most_common()),
            "user_types": dict(user_types.most_common()),
            "course_issues": dict(course_issues.most_common()),
            "learning_platform_issues": dict(learning_platform_issues.most_common())
        }
    
    def _analyze_performance_issues(self, performance_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze site performance issues."""
        if not performance_conversations:
            return {"total_performance_issues": 0, "performance_issue_types": {}, "optimization_areas": {}}
        
        performance_issue_types = Counter()
        optimization_areas = Counter()
        performance_metrics = Counter()
        
        for conv in performance_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify performance issue types
            if 'slow' in text or 'speed' in text:
                performance_issue_types['Slow Loading'] += 1
            elif 'timeout' in text:
                performance_issue_types['Timeout Issues'] += 1
            elif 'cache' in text:
                performance_issue_types['Cache Issues'] += 1
            elif 'cdn' in text:
                performance_issue_types['CDN Issues'] += 1
            elif 'bandwidth' in text:
                performance_issue_types['Bandwidth Issues'] += 1
            else:
                performance_issue_types['Other Performance Issues'] += 1
            
            # Identify optimization areas
            if 'image' in text:
                optimization_areas['Image Optimization'] += 1
            elif 'css' in text or 'javascript' in text or 'js' in text:
                optimization_areas['Code Optimization'] += 1
            elif 'database' in text or 'db' in text:
                optimization_areas['Database Optimization'] += 1
            elif 'server' in text:
                optimization_areas['Server Optimization'] += 1
        
        return {
            "total_performance_issues": len(performance_conversations),
            "performance_issue_types": dict(performance_issue_types.most_common()),
            "optimization_areas": dict(optimization_areas.most_common()),
            "performance_metrics": dict(performance_metrics.most_common())
        }
    
    def _analyze_configuration_issues(self, configuration_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze site configuration and setup issues."""
        if not configuration_conversations:
            return {"total_configuration_issues": 0, "configuration_issue_types": {}, "setup_areas": {}}
        
        configuration_issue_types = Counter()
        setup_areas = Counter()
        hosting_issues = Counter()
        
        for conv in configuration_conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify configuration issue types
            if 'setup' in text or 'install' in text:
                configuration_issue_types['Setup Issues'] += 1
            elif 'settings' in text or 'configuration' in text:
                configuration_issue_types['Settings Issues'] += 1
            elif 'deploy' in text or 'deployment' in text:
                configuration_issue_types['Deployment Issues'] += 1
            elif 'hosting' in text:
                configuration_issue_types['Hosting Issues'] += 1
            else:
                configuration_issue_types['Other Configuration Issues'] += 1
            
            # Identify setup areas
            if 'theme' in text:
                setup_areas['Theme Setup'] += 1
            elif 'plugin' in text:
                setup_areas['Plugin Setup'] += 1
            elif 'database' in text:
                setup_areas['Database Setup'] += 1
            elif 'email' in text:
                setup_areas['Email Setup'] += 1
            elif 'security' in text:
                setup_areas['Security Setup'] += 1
        
        return {
            "total_configuration_issues": len(configuration_conversations),
            "configuration_issue_types": dict(configuration_issue_types.most_common()),
            "setup_areas": dict(setup_areas.most_common()),
            "hosting_issues": dict(hosting_issues.most_common())
        }
    
    def _calculate_sites_metrics(self, conversations: List[Dict[str, Any]], classified: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Calculate overall sites metrics."""
        total_conversations = len(conversations)
        
        # Calculate percentages
        domain_percentage = (len(classified['domain']) / total_conversations * 100) if total_conversations > 0 else 0
        publishing_percentage = (len(classified['publishing']) / total_conversations * 100) if total_conversations > 0 else 0
        education_percentage = (len(classified['education']) / total_conversations * 100) if total_conversations > 0 else 0
        performance_percentage = (len(classified['performance']) / total_conversations * 100) if total_conversations > 0 else 0
        configuration_percentage = (len(classified['configuration']) / total_conversations * 100) if total_conversations > 0 else 0
        
        # Calculate resolution rates
        resolved_conversations = sum(1 for conv in conversations if conv.get('state', '').lower() == 'closed')
        resolution_rate = (resolved_conversations / total_conversations) if total_conversations > 0 else 0
        
        return {
            "total_sites_conversations": total_conversations,
            "category_distribution": {
                "domain_percentage": domain_percentage,
                "publishing_percentage": publishing_percentage,
                "education_percentage": education_percentage,
                "performance_percentage": performance_percentage,
                "configuration_percentage": configuration_percentage
            },
            "overall_resolution_rate": resolution_rate,
            "resolved_conversations": resolved_conversations
        }
    
    def _identify_sites_trends(self, conversations: List[Dict[str, Any]], start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Identify sites trends over time."""
        # Group conversations by date and sites type
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
                
                sites_type = conv.get('sites_type', 'other')
                if date_key not in daily_types:
                    daily_types[date_key] = Counter()
                daily_types[date_key][sites_type] += 1
        
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
    
    def _identify_common_sites_issues(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify common sites issues and patterns."""
        issue_patterns = Counter()
        issue_examples = {}
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Identify common issue patterns
            if 'domain' in text and 'not working' in text:
                issue_patterns['Domain Not Working'] += 1
                if 'Domain Not Working' not in issue_examples:
                    issue_examples['Domain Not Working'] = text[:200] + "..."
            
            elif 'publish' in text and 'failed' in text:
                issue_patterns['Publishing Failed'] += 1
                if 'Publishing Failed' not in issue_examples:
                    issue_examples['Publishing Failed'] = text[:200] + "..."
            
            elif 'education' in text and 'access' in text:
                issue_patterns['Education Access Issues'] += 1
                if 'Education Access Issues' not in issue_examples:
                    issue_examples['Education Access Issues'] = text[:200] + "..."
            
            elif 'performance' in text and 'slow' in text:
                issue_patterns['Site Performance Issues'] += 1
                if 'Site Performance Issues' not in issue_examples:
                    issue_examples['Site Performance Issues'] = text[:200] + "..."
            
            elif 'setup' in text and 'configuration' in text:
                issue_patterns['Site Setup Issues'] += 1
                if 'Site Setup Issues' not in issue_examples:
                    issue_examples['Site Setup Issues'] = text[:200] + "..."
        
        # Format common issues
        common_issues = []
        for issue, count in issue_patterns.most_common(10):
            common_issues.append({
                "issue": issue,
                "count": count,
                "example": issue_examples.get(issue, "No example available")
            })
        
        return common_issues
    
    def _analyze_sites_satisfaction(self, conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze customer satisfaction with sites interactions."""
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
        """Identify macro opportunities from sites conversations."""
        macro_patterns = Counter()
        macro_examples = {}
        
        for conv in conversations:
            text = self._extract_conversation_text(conv).lower()
            
            # Look for common response patterns that could be macros
            if 'domain' in text and ('setup' in text or 'configuration' in text):
                macro_patterns['Domain Setup Instructions'] += 1
                if 'Domain Setup Instructions' not in macro_examples:
                    macro_examples['Domain Setup Instructions'] = text[:300] + "..."
            
            elif 'publish' in text and ('how to' in text or 'step' in text):
                macro_patterns['Publishing Instructions'] += 1
                if 'Publishing Instructions' not in macro_examples:
                    macro_examples['Publishing Instructions'] = text[:300] + "..."
            
            elif 'education' in text and ('access' in text or 'enrollment' in text):
                macro_patterns['Education Access Help'] += 1
                if 'Education Access Help' not in macro_examples:
                    macro_examples['Education Access Help'] = text[:300] + "..."
            
            elif 'performance' in text and ('optimization' in text or 'speed' in text):
                macro_patterns['Performance Optimization Tips'] += 1
                if 'Performance Optimization Tips' not in macro_examples:
                    macro_examples['Performance Optimization Tips'] = text[:300] + "..."
        
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
    
    def _get_ai_analysis_prompt(self, data_summary: str) -> str:
        """Get AI analysis prompt for sites analysis."""
        return PromptTemplates.get_custom_analysis_prompt(
            custom_prompt="Analyze sites conversations focusing on domain issues, publishing problems, education topics, performance issues, and site configuration",
            start_date="",
            end_date="",
            intercom_data=data_summary
        )
