"""
General query builder for flexible Intercom data exploration.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryOperator(Enum):
    """Query operators for filtering."""
    EQUALS = "="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    CONTAINS = "~"
    NOT_CONTAINS = "!~"
    IN = "in"
    NOT_IN = "!in"


class QueryField(Enum):
    """Available fields for querying."""
    # Conversation fields
    CONVERSATION_ID = "id"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    CLOSED_AT = "closed_at"
    STATE = "state"
    CONVERSATION_RATING = "conversation_rating"
    
    # Source fields
    SOURCE_TYPE = "source.type"
    SOURCE_SUBJECT = "source.subject"
    SOURCE_BODY = "source.body"
    
    # Contact fields
    CONTACT_ID = "contacts.id"
    CONTACT_EMAIL = "contacts.email"
    CONTACT_NAME = "contacts.name"
    CONTACT_COUNTRY = "contacts.location.country"
    CONTACT_CITY = "contacts.location.city"
    USER_TIER = "contacts.custom_attributes.tier"
    
    # Conversation parts
    HAS_AGENT_RESPONSE = "conversation_parts.has_admin"
    MESSAGE_COUNT = "conversation_parts.count"
    
    # Custom fields
    RESPONSE_TIME = "response_time"
    RESOLUTION_TIME = "resolution_time"
    TEXT_LENGTH = "text_length"


@dataclass
class QueryCondition:
    """A single query condition."""
    field: str
    operator: QueryOperator
    value: Any
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Intercom API format."""
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value
        }


@dataclass
class QueryGroup:
    """A group of query conditions with logical operator."""
    conditions: List[Union[QueryCondition, 'QueryGroup']]
    operator: str = "AND"  # AND or OR
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to Intercom API format."""
        if len(self.conditions) == 1:
            condition = self.conditions[0]
            if isinstance(condition, QueryGroup):
                return condition.to_dict()
            else:
                return condition.to_dict()
        
        return {
            "operator": self.operator,
            "value": [
                condition.to_dict() if isinstance(condition, QueryCondition) 
                else condition.to_dict() 
                for condition in self.conditions
            ]
        }


class QueryBuilder:
    """Builder for creating flexible Intercom queries."""
    
    def __init__(self):
        self.conditions: List[Union[QueryCondition, QueryGroup]] = []
        self.logical_operator = "AND"
        self.logger = logging.getLogger(__name__)
    
    def add_condition(
        self, 
        field: str, 
        operator: QueryOperator, 
        value: Any
    ) -> 'QueryBuilder':
        """Add a single condition to the query."""
        condition = QueryCondition(field, operator, value)
        self.conditions.append(condition)
        return self
    
    def add_group(self, group: QueryGroup) -> 'QueryBuilder':
        """Add a group of conditions to the query."""
        self.conditions.append(group)
        return self
    
    def set_logical_operator(self, operator: str) -> 'QueryBuilder':
        """Set the logical operator for combining conditions."""
        self.logical_operator = operator
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build the final query."""
        if not self.conditions:
            return {}
        
        if len(self.conditions) == 1:
            condition = self.conditions[0]
            if isinstance(condition, QueryGroup):
                return condition.to_dict()
            else:
                return condition.to_dict()
        
        return {
            "operator": self.logical_operator,
            "value": [
                condition.to_dict() if isinstance(condition, QueryCondition) 
                else condition.to_dict() 
                for condition in self.conditions
            ]
        }
    
    # Convenience methods for common queries
    def date_range(self, start_date: datetime, end_date: datetime) -> 'QueryBuilder':
        """Add date range filter."""
        self.add_condition(QueryField.CREATED_AT.value, QueryOperator.GREATER_THAN_OR_EQUAL, int(start_date.timestamp()))
        self.add_condition(QueryField.CREATED_AT.value, QueryOperator.LESS_THAN_OR_EQUAL, int(end_date.timestamp()))
        return self
    
    def last_days(self, days: int) -> 'QueryBuilder':
        """Add filter for last N days."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return self.date_range(start_date, end_date)
    
    def last_weeks(self, weeks: int) -> 'QueryBuilder':
        """Add filter for last N weeks."""
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)
        return self.date_range(start_date, end_date)
    
    def last_months(self, months: int) -> 'QueryBuilder':
        """Add filter for last N months."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        return self.date_range(start_date, end_date)
    
    def state(self, state: str) -> 'QueryBuilder':
        """Add state filter."""
        return self.add_condition(QueryField.STATE.value, QueryOperator.EQUALS, state)
    
    def source_type(self, source_type: str) -> 'QueryBuilder':
        """Add source type filter."""
        return self.add_condition(QueryField.SOURCE_TYPE.value, QueryOperator.EQUALS, source_type)
    
    def contains_text(self, text: str) -> 'QueryBuilder':
        """Add text search filter."""
        return self.add_condition(QueryField.SOURCE_BODY.value, QueryOperator.CONTAINS, text)
    
    def country(self, country: str) -> 'QueryBuilder':
        """Add country filter."""
        return self.add_condition(QueryField.CONTACT_COUNTRY.value, QueryOperator.EQUALS, country)
    
    def user_tier(self, tier: str) -> 'QueryBuilder':
        """Add user tier filter."""
        return self.add_condition(QueryField.USER_TIER.value, QueryOperator.EQUALS, tier)
    
    def has_rating(self) -> 'QueryBuilder':
        """Add filter for conversations with ratings."""
        return self.add_condition(QueryField.CONVERSATION_RATING.value, QueryOperator.GREATER_THAN, 0)
    
    def rating_range(self, min_rating: float, max_rating: float) -> 'QueryBuilder':
        """Add rating range filter."""
        self.add_condition(QueryField.CONVERSATION_RATING.value, QueryOperator.GREATER_THAN_OR_EQUAL, min_rating)
        self.add_condition(QueryField.CONVERSATION_RATING.value, QueryOperator.LESS_THAN_OR_EQUAL, max_rating)
        return self
    
    def has_agent_response(self) -> 'QueryBuilder':
        """Add filter for conversations with agent responses."""
        # This would need to be implemented as a custom filter
        # since Intercom doesn't have a direct field for this
        return self
    
    def countries(self, countries: List[str]) -> 'QueryBuilder':
        """Add filter for multiple countries."""
        return self.add_condition(QueryField.CONTACT_COUNTRY.value, QueryOperator.IN, countries)
    
    def exclude_countries(self, countries: List[str]) -> 'QueryBuilder':
        """Add filter to exclude countries."""
        return self.add_condition(QueryField.CONTACT_COUNTRY.value, QueryOperator.NOT_IN, countries)
    
    def source_types(self, source_types: List[str]) -> 'QueryBuilder':
        """Add filter for multiple source types."""
        return self.add_condition(QueryField.SOURCE_TYPE.value, QueryOperator.IN, source_types)
    
    def states(self, states: List[str]) -> 'QueryBuilder':
        """Add filter for multiple states."""
        return self.add_condition(QueryField.STATE.value, QueryOperator.IN, states)
    
    def user_tiers(self, tiers: List[str]) -> 'QueryBuilder':
        """Add filter for multiple user tiers."""
        return self.add_condition(QueryField.USER_TIER.value, QueryOperator.IN, tiers)


class GeneralQueryService:
    """Service for executing general queries against Intercom data."""
    
    def __init__(self, intercom_service, data_exporter):
        self.intercom_service = intercom_service
        self.data_exporter = data_exporter
        self.logger = logging.getLogger(__name__)
    
    async def execute_query(
        self, 
        query: Dict[str, Any], 
        max_pages: Optional[int] = None,
        export_format: str = "excel"
    ) -> Dict[str, Any]:
        """Execute a general query and return results."""
        self.logger.info("Executing general query")
        
        # Fetch conversations
        conversations = await self.intercom_service.fetch_conversations_by_query(
            query, max_pages=max_pages
        )
        
        self.logger.info(f"Found {len(conversations)} conversations")
        
        # Export data
        export_results = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_format in ["excel", "both"]:
            excel_path = self.data_exporter.export_conversations_to_excel(
                conversations, f"query_results_{timestamp}"
            )
            export_results["excel"] = excel_path
        
        if export_format in ["csv", "both"]:
            csv_paths = self.data_exporter.export_conversations_to_csv(
                conversations, f"query_results_{timestamp}"
            )
            export_results["csv"] = csv_paths
        
        if export_format == "json":
            json_path = self.data_exporter.export_raw_data_to_json(
                conversations, f"query_results_{timestamp}"
            )
            export_results["json"] = json_path
        
        if export_format == "parquet":
            parquet_path = self.data_exporter.export_to_parquet(
                conversations, f"query_results_{timestamp}"
            )
            export_results["parquet"] = parquet_path
        
        return {
            "query": query,
            "total_conversations": len(conversations),
            "export_results": export_results,
            "conversations": conversations[:10]  # Sample for preview
        }
    
    async def get_query_suggestions(self) -> Dict[str, List[str]]:
        """Get suggested queries for common use cases."""
        return {
            "time_based": [
                "Last 7 days",
                "Last 30 days", 
                "Last quarter",
                "This month",
                "Last month"
            ],
            "state_based": [
                "Open conversations",
                "Closed conversations",
                "Snoozed conversations"
            ],
            "source_based": [
                "Email conversations",
                "Chat conversations",
                "Phone conversations"
            ],
            "satisfaction_based": [
                "High satisfaction (4.5+)",
                "Low satisfaction (<3.0)",
                "Rated conversations only"
            ],
            "geographic_based": [
                "US customers",
                "European customers",
                "Tier 1 countries"
            ],
            "content_based": [
                "Billing related",
                "Technical issues",
                "Product questions",
                "Account management"
            ]
        }
    
    def build_suggested_query(self, suggestion_type: str, suggestion: str) -> Dict[str, Any]:
        """Build a query from a suggestion."""
        builder = QueryBuilder()
        
        if suggestion_type == "time_based":
            if suggestion == "Last 7 days":
                builder.last_days(7)
            elif suggestion == "Last 30 days":
                builder.last_days(30)
            elif suggestion == "Last quarter":
                builder.last_months(3)
            elif suggestion == "This month":
                now = datetime.now()
                start_of_month = datetime(now.year, now.month, 1)
                builder.date_range(start_of_month, now)
            elif suggestion == "Last month":
                now = datetime.now()
                if now.month == 1:
                    start_of_last_month = datetime(now.year - 1, 12, 1)
                    end_of_last_month = datetime(now.year, 1, 1)
                else:
                    start_of_last_month = datetime(now.year, now.month - 1, 1)
                    end_of_last_month = datetime(now.year, now.month, 1)
                builder.date_range(start_of_last_month, end_of_last_month)
        
        elif suggestion_type == "state_based":
            if suggestion == "Open conversations":
                builder.state("open")
            elif suggestion == "Closed conversations":
                builder.state("closed")
            elif suggestion == "Snoozed conversations":
                builder.state("snoozed")
        
        elif suggestion_type == "source_based":
            if suggestion == "Email conversations":
                builder.source_type("email")
            elif suggestion == "Chat conversations":
                builder.source_type("chat")
            elif suggestion == "Phone conversations":
                builder.source_type("phone")
        
        elif suggestion_type == "satisfaction_based":
            if suggestion == "High satisfaction (4.5+)":
                builder.rating_range(4.5, 5.0)
            elif suggestion == "Low satisfaction (<3.0)":
                builder.rating_range(1.0, 3.0)
            elif suggestion == "Rated conversations only":
                builder.has_rating()
        
        elif suggestion_type == "geographic_based":
            if suggestion == "US customers":
                builder.country("United States")
            elif suggestion == "European customers":
                european_countries = [
                    "France", "Germany", "United Kingdom", "Spain", "Italy", 
                    "Netherlands", "Belgium", "Sweden", "Norway", "Denmark"
                ]
                builder.countries(european_countries)
            elif suggestion == "Tier 1 countries":
                tier1_countries = [
                    "United States", "Brazil", "Canada", "Mexico", "France",
                    "United Kingdom", "Germany", "Spain", "South Korea", 
                    "Japan", "Australia"
                ]
                builder.countries(tier1_countries)
        
        elif suggestion_type == "content_based":
            if suggestion == "Billing related":
                builder.contains_text("billing")
            elif suggestion == "Technical issues":
                builder.contains_text("error")
            elif suggestion == "Product questions":
                builder.contains_text("how to")
            elif suggestion == "Account management":
                builder.contains_text("account")
        
        return builder.build()

