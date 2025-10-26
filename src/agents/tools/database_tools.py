"""Database query tools for conversation analysis."""

import logging
from typing import Optional, List, Dict, Any

from src.agents.tools.base_tool import BaseTool, ToolDefinition, ToolParameter, ToolResult
from src.services.duckdb_storage import DuckDBStorage


class QueryConversationsTool(BaseTool):
    """Tool for querying the conversation database with flexible filters."""

    def __init__(self):
        """Initialize the QueryConversationsTool."""
        super().__init__(
            name="query_conversations",
            description="Query conversation database to find specific conversations matching criteria. Supports filtering by category, admin, rating range, escalation status, and result limit."
        )
        self.logger = logging.getLogger(__name__)

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
            ToolDefinition with schema for query parameters
        """
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="category",
                    type="string",
                    description="Primary category to filter (e.g., 'Billing', 'Bug', 'API', 'Sites')",
                    required=False
                ),
                ToolParameter(
                    name="admin_id",
                    type="string",
                    description="Filter by specific admin ID (e.g., '7890123')",
                    required=False
                ),
                ToolParameter(
                    name="min_rating",
                    type="number",
                    description="Minimum CSAT rating (1-5, inclusive)",
                    required=False
                ),
                ToolParameter(
                    name="max_rating",
                    type="number",
                    description="Maximum CSAT rating (1-5, inclusive)",
                    required=False
                ),
                ToolParameter(
                    name="escalated",
                    type="boolean",
                    description="Filter to escalated conversations only (conversations in escalations table)",
                    required=False
                ),
                ToolParameter(
                    name="limit",
                    type="integer",
                    description="Maximum number of results to return (default: 100, max: 1000)",
                    required=False
                )
            ]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute a database query with the provided filters.

        Args:
            **kwargs: Query parameters (category, admin_id, min_rating, max_rating, escalated, limit)

        Returns:
            ToolResult with conversations list and query metadata
        """
        # Check storage availability
        if self.storage is None:
            return ToolResult(
                success=False,
                data=None,
                error_message="Database storage not available"
            )

        # Extract parameters from kwargs
        category = kwargs.get('category')
        admin_id = kwargs.get('admin_id')
        min_rating = kwargs.get('min_rating')
        max_rating = kwargs.get('max_rating')
        escalated = kwargs.get('escalated')

        try:
            # Parse and validate limit safely inside try block
            raw_limit = kwargs.get('limit', 100)
            try:
                parsed_limit = int(raw_limit)
            except (ValueError, TypeError):
                parsed_limit = 100
            # Clamp to maximum of 1000 and minimum of 1
            limit = max(1, min(parsed_limit, 1000))
            # Build SQL query dynamically
            select_clause = """
                SELECT DISTINCT c.id, c.created_at, c.updated_at, c.state,
                       c.admin_assignee_id, c.conversation_rating, c.count_reopens,
                       c.time_to_admin_reply, c.handling_time, c.count_conversation_parts,
                       cc.primary_category AS category, cc.subcategory AS subcategory
            """

            # Build FROM clause with conditional joins
            from_clause = "FROM conversations c"

            # Add category join - use LEFT JOIN to always include category/subcategory fields
            from_clause += " LEFT JOIN conversation_categories cc ON c.id = cc.conversation_id"

            # Add escalation join if needed
            if escalated:
                from_clause += " JOIN escalations e ON c.id = e.conversation_id"

            # Build WHERE clause dynamically
            where_clauses = []
            params = {}

            if category:
                where_clauses.append("cc.primary_category = $category")
                params['category'] = category

            if admin_id:
                where_clauses.append("c.admin_assignee_id = $admin_id")
                params['admin_id'] = admin_id

            if min_rating is not None:
                where_clauses.append("c.conversation_rating >= $min_rating")
                params['min_rating'] = min_rating

            if max_rating is not None:
                where_clauses.append("c.conversation_rating <= $max_rating")
                params['max_rating'] = max_rating

            # Combine WHERE clauses
            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

            # Build complete SQL query
            sql = f"""
                {select_clause}
                {from_clause}
                WHERE {where_clause}
                ORDER BY c.created_at DESC
                LIMIT $limit
            """

            params['limit'] = limit

            # Execute query
            rows = self.storage.conn.execute(sql, params).fetchall()

            # Convert rows to dictionaries
            conversations = []
            for row in rows:
                conv_dict = {
                    'id': row[0],
                    'created_at': row[1].isoformat() if row[1] else None,
                    'updated_at': row[2].isoformat() if row[2] else None,
                    'state': row[3],
                    'admin_assignee_id': row[4],
                    'conversation_rating': row[5],
                    'count_reopens': row[6],
                    'time_to_admin_reply': row[7],
                    'handling_time': row[8],
                    'count_conversation_parts': row[9],
                    'category': row[10],
                    'subcategory': row[11]
                }
                conversations.append(conv_dict)

            # Build result metadata
            result_data = {
                'conversations': conversations,
                'count': len(conversations),
                'query_filters': {
                    'category': category,
                    'admin_id': admin_id,
                    'rating_range': {
                        'min': min_rating,
                        'max': max_rating
                    } if min_rating or max_rating else None,
                    'escalated': escalated,
                    'limit': limit
                },
                'truncated': len(conversations) == limit
            }

            return ToolResult(success=True, data=result_data)

        except Exception as e:
            self.logger.error(f"Database query failed: {e}")
            return ToolResult(
                success=False,
                data=None,
                error_message=f"Database query failed: {str(e)}"
            )
