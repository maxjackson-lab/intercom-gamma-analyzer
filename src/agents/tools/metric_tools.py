"""
Metric calculation tools for performance analysis.

This module provides tools for calculating key performance metrics:
- First Contact Resolution (FCR)
- Customer Satisfaction (CSAT)
"""

from src.agents.tools.base_tool import BaseTool, ToolDefinition, ToolParameter, ToolResult
from src.services.duckdb_storage import DuckDBStorage
from typing import Optional, List, Dict, Any
import logging


class CalculateFCRTool(BaseTool):
    """
    Calculate First Contact Resolution (FCR) rate for conversations.

    FCR measures the percentage of closed conversations that were resolved
    without reopening. Formula: (closed - reopened) / closed
    """

    def __init__(self):
        """Initialize the FCR calculation tool."""
        super().__init__(
            name="calculate_fcr",
            description="Calculate First Contact Resolution (FCR) rate for a set of conversations. FCR measures the percentage of closed conversations that were resolved without reopening."
        )

        # Initialize database storage
        try:
            self.storage = DuckDBStorage()
        except Exception as e:
            self.logger.warning(f"Failed to initialize DuckDB storage: {e}")
            self.storage = None

    def get_definition(self) -> ToolDefinition:
        """
        Get the tool definition for OpenAI function calling.

        Returns:
            ToolDefinition with parameters for FCR calculation
        """
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="conversation_ids",
                    type="array",
                    description="List of conversation IDs to calculate FCR for (optional, if not provided calculates for all conversations matching other filters)",
                    required=False
                ),
                ToolParameter(
                    name="category",
                    type="string",
                    description="Calculate FCR for a specific primary category (e.g., 'Billing', 'Bug', 'API')",
                    required=False
                ),
                ToolParameter(
                    name="admin_id",
                    type="string",
                    description="Calculate FCR for a specific agent by admin_assignee_id",
                    required=False
                ),
                ToolParameter(
                    name="agent_id",
                    type="string",
                    description="[DEPRECATED: Use admin_id] Calculate FCR for a specific agent by admin_assignee_id",
                    required=False
                )
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute FCR calculation with optional filters.

        Args:
            conversation_ids: Optional list of conversation IDs to filter
            category: Optional primary category to filter
            admin_id: Optional admin_assignee_id to filter (preferred)
            agent_id: Optional admin_assignee_id to filter (deprecated, use admin_id)

        Returns:
            ToolResult with FCR metrics or error
        """
        # Extract parameters
        conversation_ids = kwargs.get('conversation_ids')
        category = kwargs.get('category')
        # Prefer admin_id over agent_id for backward compatibility
        admin_id = kwargs.get('admin_id') or kwargs.get('agent_id')

        # Check storage availability
        if self.storage is None:
            return ToolResult(
                success=False,
                data=None,
                error_message="Database storage not available"
            )

        # Handle empty conversation_ids list - return zeroed metrics
        if conversation_ids is not None and len(conversation_ids) == 0:
            filters_applied = {'conversation_ids_count': 0}
            if category:
                filters_applied['category'] = category
            if admin_id:
                filters_applied['admin_id'] = admin_id

            return ToolResult(
                success=True,
                data={
                    'fcr_rate': 0.0,
                    'closed_count': 0,
                    'reopened_count': 0,
                    'fcr_count': 0,
                    'formula': '(closed - reopened) / closed',
                    'filters_applied': filters_applied
                }
            )

        try:
            # Build dynamic SQL query
            select_clause = """
                SELECT
                    COALESCE(COUNT(*), 0) as closed_count,
                    COALESCE(SUM(CASE WHEN c.count_reopens > 0 THEN 1 ELSE 0 END), 0) as reopened_count,
                    COALESCE(SUM(CASE WHEN c.count_reopens = 0 THEN 1 ELSE 0 END), 0) as fcr_count
            """

            # Build FROM clause with optional category join
            if category:
                from_clause = """
                    FROM conversations c
                    LEFT JOIN conversation_categories cc ON c.id = cc.conversation_id
                """
            else:
                from_clause = "FROM conversations c"

            # Build WHERE clause dynamically
            where_clauses = ["c.state = 'closed'"]
            params = {}

            # Add conversation_ids filter
            if conversation_ids:
                placeholders = ','.join([f'$id_{i}' for i in range(len(conversation_ids))])
                where_clauses.append(f"c.id IN ({placeholders})")
                for i, cid in enumerate(conversation_ids):
                    params[f'id_{i}'] = cid

            # Add category filter
            if category:
                where_clauses.append("cc.primary_category = $category")
                params['category'] = category

            # Add admin_id filter
            if admin_id:
                where_clauses.append("c.admin_assignee_id = $admin_id")
                params['admin_id'] = admin_id

            where_clause = " AND ".join(where_clauses)

            # Construct full query
            sql = f"{select_clause} {from_clause} WHERE {where_clause}"

            # Execute query
            result = self.storage.conn.execute(sql, params).fetchone()

            # Extract results
            closed_count = result[0] or 0
            reopened_count = result[1] or 0
            fcr_count = result[2] or 0

            # Calculate FCR metrics
            fcr_rate = fcr_count / closed_count if closed_count > 0 else 0.0

            # Build filters summary
            filters_applied = {}
            if conversation_ids:
                filters_applied['conversation_ids_count'] = len(conversation_ids)
            if category:
                filters_applied['category'] = category
            if admin_id:
                filters_applied['admin_id'] = admin_id

            # Build result data
            result_data = {
                'fcr_rate': round(fcr_rate, 4),
                'closed_count': closed_count,
                'reopened_count': reopened_count,
                'fcr_count': fcr_count,
                'formula': '(closed - reopened) / closed',
                'filters_applied': filters_applied
            }

            return ToolResult(success=True, data=result_data)

        except Exception as e:
            self.logger.error(f"FCR calculation failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error_message=f"FCR calculation failed: {str(e)}"
            )


class CalculateCSATTool(BaseTool):
    """
    Calculate average Customer Satisfaction (CSAT) score for conversations.

    CSAT is measured on a 1-5 scale where:
    - 1-2 are negative
    - 3 is neutral
    - 4-5 are positive
    """

    def __init__(self):
        """Initialize the CSAT calculation tool."""
        super().__init__(
            name="calculate_csat",
            description="Calculate average CSAT (Customer Satisfaction) score for conversations. CSAT is measured on a 1-5 scale where 1-2 are negative, 3 is neutral, and 4-5 are positive."
        )

        # Initialize database storage
        try:
            self.storage = DuckDBStorage()
        except Exception as e:
            self.logger.warning(f"Failed to initialize DuckDB storage: {e}")
            self.storage = None

    def get_definition(self) -> ToolDefinition:
        """
        Get the tool definition for OpenAI function calling.

        Returns:
            ToolDefinition with parameters for CSAT calculation
        """
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="conversation_ids",
                    type="array",
                    description="List of conversation IDs to calculate CSAT for (optional, if not provided calculates for all conversations matching other filters)",
                    required=False
                ),
                ToolParameter(
                    name="admin_id",
                    type="string",
                    description="Calculate CSAT for specific agent by admin_assignee_id",
                    required=False
                ),
                ToolParameter(
                    name="agent_id",
                    type="string",
                    description="[DEPRECATED: Use admin_id] Calculate CSAT for specific agent by admin_assignee_id",
                    required=False
                ),
                ToolParameter(
                    name="category",
                    type="string",
                    description="Calculate CSAT for a specific primary category (e.g., 'Billing', 'Bug', 'API')",
                    required=False
                )
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute CSAT calculation with optional filters.

        Args:
            conversation_ids: Optional list of conversation IDs to filter
            admin_id: Optional admin_assignee_id to filter (preferred)
            agent_id: Optional admin_assignee_id to filter (deprecated, use admin_id)
            category: Optional primary category to filter

        Returns:
            ToolResult with CSAT metrics or error
        """
        # Extract parameters
        conversation_ids = kwargs.get('conversation_ids')
        # Prefer admin_id over agent_id for backward compatibility
        admin_id = kwargs.get('admin_id') or kwargs.get('agent_id')
        category = kwargs.get('category')

        # Check storage availability
        if self.storage is None:
            return ToolResult(
                success=False,
                data=None,
                error_message="Database storage not available"
            )

        # Handle empty conversation_ids list - return zeroed metrics
        if conversation_ids is not None and len(conversation_ids) == 0:
            filters_applied = {'conversation_ids_count': 0}
            if admin_id:
                filters_applied['admin_id'] = admin_id
            if category:
                filters_applied['category'] = category

            return ToolResult(
                success=True,
                data={
                    'avg_csat': 0.0,
                    'survey_count': 0,
                    'negative_count': 0,
                    'negative_percentage': 0.0,
                    'positive_count': 0,
                    'positive_percentage': 0.0,
                    'filters_applied': filters_applied
                }
            )

        try:
            # Build dynamic SQL query
            select_clause = """
                SELECT
                    AVG(c.conversation_rating) as avg_csat,
                    COUNT(*) as survey_count,
                    SUM(CASE WHEN c.conversation_rating <= 2 THEN 1 ELSE 0 END) as negative_count,
                    SUM(CASE WHEN c.conversation_rating >= 4 THEN 1 ELSE 0 END) as positive_count
            """

            # Build FROM clause with optional category join
            if category:
                from_clause = """
                    FROM conversations c
                    LEFT JOIN conversation_categories cc ON c.id = cc.conversation_id
                """
            else:
                from_clause = "FROM conversations c"

            # Build WHERE clause dynamically
            where_clauses = ["c.conversation_rating IS NOT NULL"]
            params = {}

            # Add conversation_ids filter
            if conversation_ids:
                placeholders = ','.join([f'$id_{i}' for i in range(len(conversation_ids))])
                where_clauses.append(f"c.id IN ({placeholders})")
                for i, cid in enumerate(conversation_ids):
                    params[f'id_{i}'] = cid

            # Add admin_id filter
            if admin_id:
                where_clauses.append("c.admin_assignee_id = $admin_id")
                params['admin_id'] = admin_id

            # Add category filter
            if category:
                where_clauses.append("cc.primary_category = $category")
                params['category'] = category

            where_clause = " AND ".join(where_clauses)

            # Construct full query
            sql = f"{select_clause} {from_clause} WHERE {where_clause}"

            # Execute query
            result = self.storage.conn.execute(sql, params).fetchone()

            # Extract results
            avg_csat = result[0] or 0.0
            survey_count = result[1] or 0
            negative_count = result[2] or 0
            positive_count = result[3] or 0

            # Calculate percentages
            negative_percentage = round(negative_count / survey_count * 100, 1) if survey_count > 0 else 0.0
            positive_percentage = round(positive_count / survey_count * 100, 1) if survey_count > 0 else 0.0

            # Build filters summary
            filters_applied = {}
            if conversation_ids:
                filters_applied['conversation_ids_count'] = len(conversation_ids)
            if admin_id:
                filters_applied['admin_id'] = admin_id
            if category:
                filters_applied['category'] = category

            # Build result data
            result_data = {
                'avg_csat': round(avg_csat, 2),
                'survey_count': survey_count,
                'negative_count': negative_count,
                'negative_percentage': negative_percentage,
                'positive_count': positive_count,
                'positive_percentage': positive_percentage,
                'filters_applied': filters_applied
            }

            return ToolResult(success=True, data=result_data)

        except Exception as e:
            self.logger.error(f"CSAT calculation failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error_message=f"CSAT calculation failed: {str(e)}"
            )
