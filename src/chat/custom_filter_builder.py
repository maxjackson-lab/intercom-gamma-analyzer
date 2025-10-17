"""
Custom Filter Builder

Builds custom filters for agent, category, date, and other criteria
to enable complex report generation like "API tickets done by Horatio agents in September".
"""

import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from .schemas import FilterSpec, FilterType, FilterOperator


@dataclass
class FilterContext:
    """Context for building custom filters."""
    agents: List[str]
    categories: List[str]
    date_ranges: List[Tuple[datetime, datetime]]
    custom_criteria: Dict[str, Any]


class CustomFilterBuilder:
    """
    Builds custom filters from natural language descriptions.
    
    Supports complex queries like:
    - "API tickets done by Horatio agents in September"
    - "Billing issues from last week by support team"
    - "High priority tickets from Q1 2025"
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Agent name patterns
        self.agent_patterns = {
            "horatio": ["horatio", "horatio agent", "horatio bot"],
            "support": ["support", "support team", "support agent"],
            "sales": ["sales", "sales team", "sales agent"],
            "engineering": ["engineering", "eng", "dev", "developer"],
            "product": ["product", "product team", "pm", "product manager"]
        }
        
        # Category patterns
        self.category_patterns = {
            "api": ["api", "api ticket", "api issue", "api problem"],
            "billing": ["billing", "billing issue", "payment", "subscription"],
            "technical": ["technical", "tech", "bug", "error", "issue"],
            "feature": ["feature", "feature request", "enhancement"],
            "integration": ["integration", "connect", "sync", "webhook"],
            "onboarding": ["onboarding", "setup", "getting started"],
            "support": ["support", "help", "question", "assistance"]
        }
        
        # Date patterns
        self.date_patterns = {
            "last_week": ["last week", "previous week", "past week"],
            "this_week": ["this week", "current week"],
            "last_month": ["last month", "previous month", "past month"],
            "this_month": ["this month", "current month"],
            "last_quarter": ["last quarter", "previous quarter", "past quarter"],
            "this_quarter": ["this quarter", "current quarter"],
            "september": ["september", "sep", "sept"],
            "october": ["october", "oct"],
            "november": ["november", "nov"],
            "december": ["december", "dec"],
            "january": ["january", "jan"],
            "february": ["february", "feb"],
            "march": ["march", "mar"],
            "april": ["april", "apr"],
            "may": ["may"],
            "june": ["june", "jun"],
            "july": ["july", "jul"],
            "august": ["august", "aug"]
        }
        
        # Priority patterns
        self.priority_patterns = {
            "high": ["high priority", "urgent", "critical", "important"],
            "medium": ["medium priority", "normal", "standard"],
            "low": ["low priority", "minor", "low"]
        }
        
        # Status patterns
        self.status_patterns = {
            "open": ["open", "new", "unresolved"],
            "closed": ["closed", "resolved", "completed", "done"],
            "pending": ["pending", "waiting", "in progress"]
        }
    
    def build_filters(self, query: str, context: Optional[FilterContext] = None) -> List[FilterSpec]:
        """
        Build custom filters from natural language query.
        
        Args:
            query: Natural language description of filters
            context: Additional context for filter building
            
        Returns:
            List of FilterSpec objects
        """
        filters = []
        query_lower = query.lower()
        
        try:
            # Extract agent filters
            agent_filters = self._extract_agent_filters(query_lower)
            filters.extend(agent_filters)
            
            # Extract category filters
            category_filters = self._extract_category_filters(query_lower)
            filters.extend(category_filters)
            
            # Extract date filters
            date_filters = self._extract_date_filters(query_lower)
            filters.extend(date_filters)
            
            # Extract priority filters
            priority_filters = self._extract_priority_filters(query_lower)
            filters.extend(priority_filters)
            
            # Extract status filters
            status_filters = self._extract_status_filters(query_lower)
            filters.extend(status_filters)
            
            # Extract custom criteria
            custom_filters = self._extract_custom_filters(query_lower, context)
            filters.extend(custom_filters)
            
            self.logger.info(f"Built {len(filters)} filters from query: {query}")
            return filters
            
        except Exception as e:
            self.logger.error(f"Error building filters from query '{query}': {e}")
            return []
    
    def _extract_agent_filters(self, query: str) -> List[FilterSpec]:
        """Extract agent-related filters."""
        filters = []
        
        for agent_type, patterns in self.agent_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    filters.append(FilterSpec(
                        field="agent",
                        operator=FilterOperator.EQUALS,
                        value=agent_type,
                        description=f"Filter by {agent_type} agent"
                    ))
                    break
        
        return filters
    
    def _extract_category_filters(self, query: str) -> List[FilterSpec]:
        """Extract category-related filters."""
        filters = []
        
        for category, patterns in self.category_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    filters.append(FilterSpec(
                        field="category",
                        operator=FilterOperator.EQUALS,
                        value=category,
                        description=f"Filter by {category} category"
                    ))
                    break
        
        return filters
    
    def _extract_date_filters(self, query: str) -> List[FilterSpec]:
        """Extract date-related filters."""
        filters = []
        
        # Check for relative date patterns
        for date_type, patterns in self.date_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    start_date, end_date = self._get_date_range(date_type)
                    if start_date and end_date:
                        filters.append(FilterSpec(
                            field="created_at",
                            operator=FilterOperator.BETWEEN,
                            value=[start_date.isoformat(), end_date.isoformat()],
                            description=f"Filter by {date_type} date range"
                        ))
                    break
        
        # Check for specific year patterns
        year_match = re.search(r'\b(202[0-9])\b', query)
        if year_match:
            year = int(year_match.group(1))
            start_date = datetime(year, 1, 1)
            end_date = datetime(year, 12, 31, 23, 59, 59)
            filters.append(FilterSpec(
                field="created_at",
                operator=FilterOperator.BETWEEN,
                value=[start_date.isoformat(), end_date.isoformat()],
                description=f"Filter by year {year}"
            ))
        
        # Check for quarter patterns
        quarter_match = re.search(r'\bq([1-4])\b', query)
        if quarter_match:
            quarter = int(quarter_match.group(1))
            year = datetime.now().year
            start_month = (quarter - 1) * 3 + 1
            start_date = datetime(year, start_month, 1)
            end_date = datetime(year, start_month + 2, 31, 23, 59, 59)
            filters.append(FilterSpec(
                field="created_at",
                operator=FilterOperator.BETWEEN,
                value=[start_date.isoformat(), end_date.isoformat()],
                description=f"Filter by Q{quarter} {year}"
            ))
        
        return filters
    
    def _extract_priority_filters(self, query: str) -> List[FilterSpec]:
        """Extract priority-related filters."""
        filters = []
        
        for priority, patterns in self.priority_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    filters.append(FilterSpec(
                        field="priority",
                        operator=FilterOperator.EQUALS,
                        value=priority,
                        description=f"Filter by {priority} priority"
                    ))
                    break
        
        return filters
    
    def _extract_status_filters(self, query: str) -> List[FilterSpec]:
        """Extract status-related filters."""
        filters = []
        
        for status, patterns in self.status_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    filters.append(FilterSpec(
                        field="status",
                        operator=FilterOperator.EQUALS,
                        value=status,
                        description=f"Filter by {status} status"
                    ))
                    break
        
        return filters
    
    def _extract_custom_filters(self, query: str, context: Optional[FilterContext] = None) -> List[FilterSpec]:
        """Extract custom criteria filters."""
        filters = []
        
        if not context:
            return filters
        
        # Check for custom criteria in context
        for field, values in context.custom_criteria.items():
            if isinstance(values, list):
                for value in values:
                    if str(value).lower() in query:
                        filters.append(FilterSpec(
                            field=field,
                            operator=FilterOperator.EQUALS,
                            value=value,
                            description=f"Filter by {field}: {value}"
                        ))
            else:
                if str(values).lower() in query:
                    filters.append(FilterSpec(
                        field=field,
                        operator=FilterOperator.EQUALS,
                        value=values,
                        description=f"Filter by {field}: {values}"
                    ))
        
        return filters
    
    def _get_date_range(self, date_type: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get date range for a given date type."""
        now = datetime.now()
        
        if date_type == "last_week":
            start = now - timedelta(days=now.weekday() + 7)
            end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
            return start.replace(hour=0, minute=0, second=0), end
        
        elif date_type == "this_week":
            start = now - timedelta(days=now.weekday())
            end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
            return start.replace(hour=0, minute=0, second=0), end
        
        elif date_type == "last_month":
            if now.month == 1:
                start = datetime(now.year - 1, 12, 1)
            else:
                start = datetime(now.year, now.month - 1, 1)
            end = datetime(now.year, now.month, 1) - timedelta(seconds=1)
            return start, end
        
        elif date_type == "this_month":
            start = datetime(now.year, now.month, 1)
            end = datetime(now.year, now.month + 1, 1) - timedelta(seconds=1)
            return start, end
        
        elif date_type == "last_quarter":
            current_quarter = (now.month - 1) // 3 + 1
            if current_quarter == 1:
                start = datetime(now.year - 1, 10, 1)
            else:
                start_month = (current_quarter - 2) * 3 + 1
                start = datetime(now.year, start_month, 1)
            end = datetime(now.year, (current_quarter - 1) * 3 + 1, 1) - timedelta(seconds=1)
            return start, end
        
        elif date_type == "this_quarter":
            current_quarter = (now.month - 1) // 3 + 1
            start_month = (current_quarter - 1) * 3 + 1
            start = datetime(now.year, start_month, 1)
            end = datetime(now.year, current_quarter * 3 + 1, 1) - timedelta(seconds=1)
            return start, end
        
        # Handle month names
        month_map = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12
        }
        
        if date_type in month_map:
            month = month_map[date_type]
            year = now.year
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
            else:
                end = datetime(year, month + 1, 1) - timedelta(seconds=1)
            return start, end
        
        return None, None
    
    def get_supported_filters(self) -> Dict[str, List[str]]:
        """Get list of supported filter types and values."""
        return {
            "agents": list(self.agent_patterns.keys()),
            "categories": list(self.category_patterns.keys()),
            "date_ranges": list(self.date_patterns.keys()),
            "priorities": list(self.priority_patterns.keys()),
            "statuses": list(self.status_patterns.keys())
        }
    
    def get_filter_examples(self) -> List[str]:
        """Get example filter queries."""
        return [
            "API tickets done by Horatio agents in September",
            "Billing issues from last week by support team",
            "High priority tickets from Q1 2025",
            "Technical problems from this month",
            "Feature requests from last quarter",
            "Open tickets by engineering team",
            "Closed issues from December 2024",
            "Integration problems by product team"
        ]
    
    def validate_filters(self, filters: List[FilterSpec]) -> Tuple[bool, List[str]]:
        """
        Validate a list of filters.
        
        Args:
            filters: List of FilterSpec objects to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        for filter_spec in filters:
            # Validate field
            if not filter_spec.field:
                errors.append("Filter field cannot be empty")
                continue
            
            # Validate operator
            if not isinstance(filter_spec.operator, FilterOperator):
                errors.append(f"Invalid operator for field '{filter_spec.field}': {filter_spec.operator}")
                continue
            
            # Validate value
            if filter_spec.value is None:
                errors.append(f"Filter value cannot be None for field '{filter_spec.field}'")
                continue
            
            # Validate date ranges
            if filter_spec.operator == FilterOperator.BETWEEN:
                if not isinstance(filter_spec.value, list) or len(filter_spec.value) != 2:
                    errors.append(f"BETWEEN operator requires a list of 2 values for field '{filter_spec.field}'")
                    continue
                
                try:
                    datetime.fromisoformat(filter_spec.value[0])
                    datetime.fromisoformat(filter_spec.value[1])
                except ValueError:
                    errors.append(f"Invalid date format in BETWEEN filter for field '{filter_spec.field}'")
        
        return len(errors) == 0, errors
